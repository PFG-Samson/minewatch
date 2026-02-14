"""
Mosaicking Module for MineWatch

Merges multiple satellite tiles when a single scene doesn't cover the entire boundary.
Handles tile alignment, resampling, and seamline blending.
"""

from __future__ import annotations
import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.mask import mask
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
import tempfile
import os

from backend.utils.coverage_validator import (
    validate_coverage, 
    validate_multi_scene_coverage,
    extract_boundary_geometry,
    CoverageResult
)
from backend.config import COVERAGE_CONFIG


# Directory for mosaic outputs
MOSAIC_DIR = Path(__file__).parent.parent / "data" / "mosaics"


def ensure_mosaic_dir():
    """Ensures the mosaic output directory exists."""
    MOSAIC_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class MosaicResult:
    """Result of a mosaic operation."""
    success: bool
    output_path: Optional[str]
    coverage_result: CoverageResult
    source_count: int
    message: str


def create_mosaic(
    raster_paths: List[str],
    output_name: str,
    boundary_geojson: Optional[dict] = None,
    method: str = "first"
) -> MosaicResult:
    """
    Creates a mosaic from multiple raster files.
    
    Args:
        raster_paths: List of paths to raster files to merge
        output_name: Name for the output mosaic file
        boundary_geojson: Optional boundary to clip the mosaic to
        method: Merge method - 'first', 'last', 'min', 'max', 'mean'
        
    Returns:
        MosaicResult with output path and metadata
    """
    ensure_mosaic_dir()
    
    if not raster_paths:
        return MosaicResult(
            success=False,
            output_path=None,
            coverage_result=CoverageResult(
                is_valid=False,
                coverage_percent=0.0,
                covered_geometry=None,
                uncovered_geometry=None,
                message="No input rasters provided"
            ),
            source_count=0,
            message="No input rasters provided"
        )
    
    # If only one raster, just copy/clip it
    if len(raster_paths) == 1:
        return _process_single_raster(raster_paths[0], output_name, boundary_geojson)
    
    try:
        # Open all datasets
        datasets = [rasterio.open(p) for p in raster_paths]
        
        # Check that all rasters have compatible CRS
        base_crs = datasets[0].crs
        for i, ds in enumerate(datasets[1:], 1):
            if ds.crs != base_crs:
                print(f"  ⚠️ Reprojecting {raster_paths[i]} from {ds.crs} to {base_crs}")
                # Handle CRS mismatch by reprojecting
                datasets[i] = _reproject_to_match(ds, datasets[0])
        
        # Merge datasets
        print(f"  Merging {len(datasets)} tiles...")
        mosaic_data, mosaic_transform = merge(
            datasets,
            method=method,
            nodata=0
        )
        
        # Get output profile from first dataset
        out_profile = datasets[0].profile.copy()
        out_profile.update(
            driver='GTiff',
            height=mosaic_data.shape[1],
            width=mosaic_data.shape[2],
            transform=mosaic_transform,
            compress='lzw'
        )
        
        # Close all input datasets
        for ds in datasets:
            ds.close()
        
        output_path = MOSAIC_DIR / f"{output_name}.tif"
        
        # Write mosaic
        with rasterio.open(output_path, 'w', **out_profile) as dst:
            dst.write(mosaic_data)
        
        print(f"  ✓ Mosaic created: {output_path}")
        
        # Clip to boundary if provided
        if boundary_geojson:
            clipped_path = MOSAIC_DIR / f"{output_name}_clipped.tif"
            clip_success = _clip_raster_to_boundary(
                str(output_path), 
                str(clipped_path), 
                boundary_geojson
            )
            if clip_success:
                output_path = clipped_path
                print(f"  ✓ Clipped to boundary: {clipped_path}")
        
        # Validate coverage
        if boundary_geojson:
            coverage = validate_coverage(
                str(output_path),
                boundary_geojson,
                min_coverage_percent=COVERAGE_CONFIG["MINIMUM_REQUIRED"],
                check_valid_data=False  # Faster, just check bounds
            )
        else:
            coverage = CoverageResult(
                is_valid=True,
                coverage_percent=100.0,
                covered_geometry=None,
                uncovered_geometry=None,
                message="No boundary provided for validation"
            )
        
        return MosaicResult(
            success=True,
            output_path=str(output_path),
            coverage_result=coverage,
            source_count=len(raster_paths),
            message=f"Successfully merged {len(raster_paths)} tiles"
        )
        
    except Exception as e:
        print(f"  ✗ Mosaic failed: {e}")
        return MosaicResult(
            success=False,
            output_path=None,
            coverage_result=CoverageResult(
                is_valid=False,
                coverage_percent=0.0,
                covered_geometry=None,
                uncovered_geometry=None,
                message=f"Mosaic error: {str(e)}"
            ),
            source_count=len(raster_paths),
            message=f"Mosaic creation failed: {str(e)}"
        )


def _process_single_raster(
    raster_path: str,
    output_name: str,
    boundary_geojson: Optional[dict]
) -> MosaicResult:
    """Processes a single raster (no mosaic needed)."""
    ensure_mosaic_dir()
    
    try:
        if boundary_geojson:
            # Clip to boundary
            output_path = MOSAIC_DIR / f"{output_name}_clipped.tif"
            clip_success = _clip_raster_to_boundary(
                raster_path,
                str(output_path),
                boundary_geojson
            )
            if not clip_success:
                output_path = Path(raster_path)
        else:
            output_path = Path(raster_path)
        
        # Validate coverage
        if boundary_geojson:
            coverage = validate_coverage(
                str(output_path),
                boundary_geojson,
                min_coverage_percent=COVERAGE_CONFIG["MINIMUM_REQUIRED"],
                check_valid_data=False
            )
        else:
            coverage = CoverageResult(
                is_valid=True,
                coverage_percent=100.0,
                covered_geometry=None,
                uncovered_geometry=None,
                message="No boundary provided"
            )
        
        return MosaicResult(
            success=True,
            output_path=str(output_path),
            coverage_result=coverage,
            source_count=1,
            message="Single raster processed"
        )
        
    except Exception as e:
        return MosaicResult(
            success=False,
            output_path=None,
            coverage_result=CoverageResult(
                is_valid=False,
                coverage_percent=0.0,
                covered_geometry=None,
                uncovered_geometry=None,
                message=f"Processing error: {str(e)}"
            ),
            source_count=1,
            message=f"Single raster processing failed: {str(e)}"
        )


def _clip_raster_to_boundary(
    input_path: str,
    output_path: str,
    boundary_geojson: dict
) -> bool:
    """Clips a raster to a GeoJSON boundary."""
    try:
        from rasterio.warp import transform_geom
        from shapely.geometry import mapping
        
        boundary_geom = extract_boundary_geometry(boundary_geojson)
        
        with rasterio.open(input_path) as src:
            # Transform boundary to raster CRS
            boundary_native = transform_geom(
                'EPSG:4326',
                src.crs,
                mapping(boundary_geom)
            )
            
            # Clip
            out_image, out_transform = mask(
                src,
                [boundary_native],
                crop=True,
                nodata=0
            )
            
            out_profile = src.profile.copy()
            out_profile.update(
                height=out_image.shape[1],
                width=out_image.shape[2],
                transform=out_transform,
                nodata=0
            )
            
            with rasterio.open(output_path, 'w', **out_profile) as dst:
                dst.write(out_image)
        
        return True
        
    except Exception as e:
        print(f"  ⚠️ Clip failed: {e}")
        return False


def _reproject_to_match(src_dataset, ref_dataset) -> rasterio.DatasetReader:
    """Reprojects a dataset to match reference CRS and resolution."""
    import tempfile
    
    dst_crs = ref_dataset.crs
    
    transform, width, height = calculate_default_transform(
        src_dataset.crs,
        dst_crs,
        src_dataset.width,
        src_dataset.height,
        *src_dataset.bounds
    )
    
    # Create temporary file for reprojected data
    tmp_file = tempfile.NamedTemporaryFile(suffix='.tif', delete=False)
    tmp_path = tmp_file.name
    tmp_file.close()
    
    kwargs = src_dataset.meta.copy()
    kwargs.update({
        'crs': dst_crs,
        'transform': transform,
        'width': width,
        'height': height
    })
    
    with rasterio.open(tmp_path, 'w', **kwargs) as dst:
        for i in range(1, src_dataset.count + 1):
            reproject(
                source=rasterio.band(src_dataset, i),
                destination=rasterio.band(dst, i),
                src_transform=src_dataset.transform,
                src_crs=src_dataset.crs,
                dst_transform=transform,
                dst_crs=dst_crs,
                resampling=Resampling.bilinear
            )
    
    return rasterio.open(tmp_path)


def create_band_mosaic_set(
    scene_band_paths: Dict[str, List[str]],
    output_prefix: str,
    boundary_geojson: Optional[dict] = None
) -> Dict[str, MosaicResult]:
    """
    Creates mosaics for a set of bands from multiple scenes.
    
    Args:
        scene_band_paths: Dict mapping band names to lists of file paths
                         e.g., {"B04": ["scene1_B04.tif", "scene2_B04.tif"], ...}
        output_prefix: Prefix for output files
        boundary_geojson: Optional boundary to clip to
        
    Returns:
        Dict mapping band names to MosaicResult
    """
    results = {}
    
    for band_name, paths in scene_band_paths.items():
        print(f"Creating mosaic for {band_name}...")
        output_name = f"{output_prefix}_{band_name}"
        result = create_mosaic(
            paths,
            output_name,
            boundary_geojson=boundary_geojson
        )
        results[band_name] = result
        
        if result.success:
            print(f"  ✓ {band_name}: {result.coverage_result.message}")
        else:
            print(f"  ✗ {band_name}: {result.message}")
    
    return results


def check_mosaic_needed(
    raster_path: str,
    boundary_geojson: dict,
    min_coverage_percent: float = None
) -> Tuple[bool, CoverageResult]:
    """
    Checks if mosaicking is needed for a single raster to cover a boundary.
    
    Args:
        raster_path: Path to the raster file
        boundary_geojson: Target boundary
        min_coverage_percent: Required coverage threshold (default from config)
        
    Returns:
        Tuple of (needs_mosaic: bool, coverage_result: CoverageResult)
    """
    if min_coverage_percent is None:
        min_coverage_percent = COVERAGE_CONFIG["MOSAIC_THRESHOLD"]
    
    coverage = validate_coverage(
        raster_path,
        boundary_geojson,
        min_coverage_percent=min_coverage_percent,
        check_valid_data=False
    )
    
    needs_mosaic = not coverage.is_valid
    return needs_mosaic, coverage
