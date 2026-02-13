"""
Coverage Validator Module for MineWatch

Validates that satellite imagery covers the entire mine boundary area.
Calculates overlap percentages and identifies coverage gaps.
"""

from __future__ import annotations
import rasterio
from rasterio.warp import transform_bounds
from shapely.geometry import box, shape, mapping
from shapely.ops import unary_union
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CoverageResult:
    """Result of a coverage validation check."""
    is_valid: bool
    coverage_percent: float
    covered_geometry: Optional[dict]  # GeoJSON of covered area
    uncovered_geometry: Optional[dict]  # GeoJSON of gaps (if any)
    message: str


def get_raster_footprint(raster_path: str) -> dict:
    """
    Gets the footprint of a raster file as a GeoJSON geometry in EPSG:4326.
    
    Args:
        raster_path: Path to the raster file
        
    Returns:
        GeoJSON geometry dict representing the raster bounds
    """
    with rasterio.open(raster_path) as src:
        # Get bounds in native CRS and transform to WGS84
        bounds = transform_bounds(src.crs, 'EPSG:4326', *src.bounds)
        # bounds = (west, south, east, north) = (minx, miny, maxx, maxy)
        footprint = box(bounds[0], bounds[1], bounds[2], bounds[3])
        return mapping(footprint)


def get_raster_valid_data_mask(raster_path: str, nodata_value: Optional[float] = 0) -> Tuple[Any, dict]:
    """
    Gets the actual valid data extent (excluding nodata pixels) as a geometry.
    
    Args:
        raster_path: Path to the raster file
        nodata_value: Value to treat as nodata (default 0 for Sentinel-2)
        
    Returns:
        Tuple of (shapely geometry of valid data, GeoJSON dict)
    """
    from rasterio.features import shapes
    from rasterio.warp import transform_geom
    import numpy as np
    
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        
        # Create mask of valid pixels
        if src.nodata is not None:
            valid_mask = (data != src.nodata).astype(np.uint8)
        else:
            valid_mask = (data != nodata_value).astype(np.uint8)
        
        # Get shapes of valid regions
        valid_shapes = []
        for geom, val in shapes(valid_mask, mask=valid_mask > 0, transform=src.transform):
            # Transform to WGS84
            geom_4326 = transform_geom(src.crs, 'EPSG:4326', geom)
            valid_shapes.append(shape(geom_4326))
        
        if not valid_shapes:
            return None, None
            
        # Union all valid shapes
        valid_union = unary_union(valid_shapes)
        return valid_union, mapping(valid_union)


def extract_boundary_geometry(boundary_geojson: dict) -> Any:
    """
    Extracts a shapely geometry from various GeoJSON formats.
    
    Args:
        boundary_geojson: GeoJSON dict (Geometry, Feature, or FeatureCollection)
        
    Returns:
        Shapely geometry object
    """
    geom_type = boundary_geojson.get("type")
    
    if geom_type in ["Point", "LineString", "Polygon", "MultiPoint", 
                     "MultiLineString", "MultiPolygon", "GeometryCollection"]:
        return shape(boundary_geojson)
    
    if geom_type == "Feature":
        return shape(boundary_geojson["geometry"])
    
    if geom_type == "FeatureCollection":
        features = boundary_geojson.get("features", [])
        if not features:
            raise ValueError("FeatureCollection has no features")
        geometries = [shape(f["geometry"]) for f in features]
        return unary_union(geometries)
    
    raise ValueError(f"Unsupported GeoJSON type: {geom_type}")


def validate_coverage(
    raster_path: str,
    boundary_geojson: dict,
    min_coverage_percent: float = 95.0,
    check_valid_data: bool = True
) -> CoverageResult:
    """
    Validates that a raster file covers the specified boundary.
    
    Args:
        raster_path: Path to the raster file
        boundary_geojson: GeoJSON of the area that should be covered
        min_coverage_percent: Minimum required coverage (default 95%)
        check_valid_data: If True, checks actual data pixels, not just bounds
        
    Returns:
        CoverageResult with validation details
    """
    try:
        boundary_geom = extract_boundary_geometry(boundary_geojson)
        boundary_area = boundary_geom.area
        
        if boundary_area == 0:
            return CoverageResult(
                is_valid=False,
                coverage_percent=0.0,
                covered_geometry=None,
                uncovered_geometry=mapping(boundary_geom),
                message="Boundary has zero area"
            )
        
        # Get raster footprint
        footprint_geojson = get_raster_footprint(raster_path)
        footprint_geom = shape(footprint_geojson)
        
        # Check if we should validate actual valid data
        if check_valid_data:
            valid_geom, _ = get_raster_valid_data_mask(raster_path)
            if valid_geom is not None:
                coverage_geom = valid_geom
            else:
                coverage_geom = footprint_geom
        else:
            coverage_geom = footprint_geom
        
        # Calculate intersection
        if not boundary_geom.intersects(coverage_geom):
            return CoverageResult(
                is_valid=False,
                coverage_percent=0.0,
                covered_geometry=None,
                uncovered_geometry=mapping(boundary_geom),
                message="Raster does not intersect boundary at all"
            )
        
        intersection = boundary_geom.intersection(coverage_geom)
        intersection_area = intersection.area
        coverage_percent = (intersection_area / boundary_area) * 100.0
        
        # Calculate uncovered area
        uncovered = boundary_geom.difference(coverage_geom)
        uncovered_geojson = mapping(uncovered) if not uncovered.is_empty else None
        
        is_valid = coverage_percent >= min_coverage_percent
        
        if is_valid:
            message = f"Coverage validated: {coverage_percent:.1f}% (>= {min_coverage_percent}%)"
        else:
            message = f"Insufficient coverage: {coverage_percent:.1f}% (< {min_coverage_percent}%)"
        
        return CoverageResult(
            is_valid=is_valid,
            coverage_percent=coverage_percent,
            covered_geometry=mapping(intersection),
            uncovered_geometry=uncovered_geojson,
            message=message
        )
        
    except Exception as e:
        return CoverageResult(
            is_valid=False,
            coverage_percent=0.0,
            covered_geometry=None,
            uncovered_geometry=None,
            message=f"Coverage validation error: {str(e)}"
        )


def validate_multi_scene_coverage(
    raster_paths: List[str],
    boundary_geojson: dict,
    min_coverage_percent: float = 95.0
) -> Tuple[CoverageResult, List[str]]:
    """
    Validates coverage from multiple raster files and identifies which are needed.
    
    Args:
        raster_paths: List of paths to raster files (same band from different scenes)
        boundary_geojson: GeoJSON of the area that should be covered
        min_coverage_percent: Minimum required coverage
        
    Returns:
        Tuple of (CoverageResult, list of paths that contribute to coverage)
    """
    try:
        boundary_geom = extract_boundary_geometry(boundary_geojson)
        boundary_area = boundary_geom.area
        
        if boundary_area == 0:
            return CoverageResult(
                is_valid=False,
                coverage_percent=0.0,
                covered_geometry=None,
                uncovered_geometry=mapping(boundary_geom),
                message="Boundary has zero area"
            ), []
        
        # Get footprints of all rasters
        contributing_paths = []
        footprints = []
        
        for path in raster_paths:
            footprint_geojson = get_raster_footprint(path)
            footprint_geom = shape(footprint_geojson)
            
            # Only include if it intersects boundary
            if boundary_geom.intersects(footprint_geom):
                footprints.append(footprint_geom)
                contributing_paths.append(path)
        
        if not footprints:
            return CoverageResult(
                is_valid=False,
                coverage_percent=0.0,
                covered_geometry=None,
                uncovered_geometry=mapping(boundary_geom),
                message="No rasters intersect the boundary"
            ), []
        
        # Union all footprints
        combined_coverage = unary_union(footprints)
        
        # Calculate intersection with boundary
        intersection = boundary_geom.intersection(combined_coverage)
        intersection_area = intersection.area
        coverage_percent = (intersection_area / boundary_area) * 100.0
        
        # Calculate uncovered area
        uncovered = boundary_geom.difference(combined_coverage)
        uncovered_geojson = mapping(uncovered) if not uncovered.is_empty else None
        
        is_valid = coverage_percent >= min_coverage_percent
        
        if is_valid:
            message = f"Combined coverage: {coverage_percent:.1f}% from {len(contributing_paths)} scene(s)"
        else:
            message = f"Insufficient combined coverage: {coverage_percent:.1f}% from {len(contributing_paths)} scene(s)"
        
        return CoverageResult(
            is_valid=is_valid,
            coverage_percent=coverage_percent,
            covered_geometry=mapping(intersection),
            uncovered_geometry=uncovered_geojson,
            message=message
        ), contributing_paths
        
    except Exception as e:
        return CoverageResult(
            is_valid=False,
            coverage_percent=0.0,
            covered_geometry=None,
            uncovered_geometry=None,
            message=f"Multi-scene coverage validation error: {str(e)}"
        ), []


def find_optimal_scenes(
    scene_footprints: List[Dict[str, Any]],
    boundary_geojson: dict,
    min_coverage_percent: float = 95.0,
    prefer_less_cloud: bool = True
) -> List[str]:
    """
    Finds the optimal set of scenes to cover a boundary.
    
    Args:
        scene_footprints: List of dicts with 'id', 'footprint' (GeoJSON), 'cloud_cover'
        boundary_geojson: Target boundary
        min_coverage_percent: Required coverage
        prefer_less_cloud: Sort by cloud cover when selecting
        
    Returns:
        List of scene IDs that provide optimal coverage
    """
    boundary_geom = extract_boundary_geometry(boundary_geojson)
    
    # Sort by cloud cover if preferred
    if prefer_less_cloud:
        scene_footprints = sorted(
            scene_footprints, 
            key=lambda x: x.get('cloud_cover', 100) or 100
        )
    
    selected_ids = []
    covered_geom = None
    
    for scene in scene_footprints:
        scene_geom = extract_boundary_geometry(scene['footprint'])
        
        # Check if this scene adds coverage
        if not boundary_geom.intersects(scene_geom):
            continue
        
        scene_contribution = boundary_geom.intersection(scene_geom)
        
        if covered_geom is None:
            covered_geom = scene_contribution
            selected_ids.append(scene['id'])
        else:
            # Check if scene adds new coverage
            new_coverage = scene_contribution.difference(covered_geom)
            if not new_coverage.is_empty and new_coverage.area > 0:
                covered_geom = unary_union([covered_geom, scene_contribution])
                selected_ids.append(scene['id'])
        
        # Check if we have enough coverage
        coverage_percent = (covered_geom.area / boundary_geom.area) * 100.0
        if coverage_percent >= min_coverage_percent:
            break
    
    return selected_ids
