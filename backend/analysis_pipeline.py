from __future__ import annotations
import numpy as np
import os
from dataclasses import dataclass, field
from typing import Any, Optional, List, Tuple, Dict
from datetime import datetime

from backend.config import (
    COVERAGE_CONFIG,
    TEMPORAL_CONFIG,
    SCENE_CONFIG,
    VALIDATION_CONFIG,
    calculate_max_scenes_needed as config_calculate_max_scenes
)
from backend.exceptions import (
    InsufficientCoverageError,
    MosaicError,
    IdenticalScenesError,
    DatabaseConnectionError,
    TemporalInconsistencyError,
    AnalysisError
)
from backend.utils.stac_downloader import (
    download_sentinel2_bands,
    download_sentinel2_bands_with_validation
)
from backend.utils.spatial import (
    calculate_ndvi, calculate_ndwi, calculate_bsi, 
    clip_raster_to_geometry, vectorize_mask
)
from backend.utils.coverage_validator import (
    validate_coverage, 
    CoverageResult,
    validate_multi_scene_coverage,
    get_raster_footprint,
    extract_boundary_geometry
)
from backend.utils.index_generator import (
    generate_index, generate_change_preview, generate_all_indices, IndexResult
)
from backend.utils.mosaicking import (
    create_band_mosaic_set,
    check_mosaic_needed,
    MosaicResult
)

from backend.alert_rules import Alert, Zone


@dataclass(frozen=True)
class ImageryScene:
    id: int
    source: str
    acquired_at: str
    cloud_cover: Optional[float]
    uri: Optional[str]


def validate_downloaded_coverage(band_paths: Dict[str, str], boundary_geojson: dict) -> float:
    """
    Validates actual pixel data coverage after download.
    
    Uses the first band as reference and checks actual valid data pixels,
    not just the raster bounds.
    
    Args:
        band_paths: Dict mapping band names to file paths
        boundary_geojson: GeoJSON boundary to validate against
        
    Returns:
        Coverage percentage (0-100)
        
    Raises:
        ValueError if band_paths is empty
    """
    if not band_paths:
        raise ValueError("No band paths provided for coverage validation")
    
    # Use first band as reference
    first_band_path = list(band_paths.values())[0]
    
    coverage_result = validate_coverage(
        first_band_path,
        boundary_geojson,
        min_coverage_percent=COVERAGE_CONFIG["MINIMUM_REQUIRED"],
        check_valid_data=VALIDATION_CONFIG["CHECK_VALID_DATA"]
    )
    
    return coverage_result.coverage_percent


def calculate_max_scenes_needed(boundary_geojson: dict) -> int:
    """
    Calculates maximum scenes needed based on boundary size.
    
    Args:
        boundary_geojson: GeoJSON boundary
        
    Returns:
        Estimated number of scenes needed
    """
    try:
        boundary_geom = extract_boundary_geometry(boundary_geojson)
        area_deg_sq = boundary_geom.area
        return config_calculate_max_scenes(area_deg_sq)
    except Exception as e:
        print(f"  ⚠️ Could not calculate max scenes from boundary: {e}")
        return SCENE_CONFIG["DEFAULT_MAX_SCENES"]


def parse_date(date_str: str) -> datetime:
    """
    Parses an ISO date string to datetime.
    
    Args:
        date_str: ISO format date string
        
    Returns:
        datetime object
    """
    # Try common formats
    for fmt in ["%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
        try:
            return datetime.strptime(date_str.split("+")[0].split("Z")[0], fmt.replace("%z", ""))
        except ValueError:
            continue
    raise ValueError(f"Could not parse date: {date_str}")


def _check_scene_footprint_coverage(
    db_conn,
    scene_uri: str,
    boundary_geojson: dict
) -> float:
    """
    Check how much of the boundary is covered by a scene's footprint.
    Uses the footprint stored in database (actual data extent from STAC).
    
    Returns:
        Coverage percentage (0-100)
    """
    import json
    from backend.utils.coverage_validator import extract_boundary_geometry
    
    try:
        row = db_conn.execute(
            "SELECT footprint_geojson FROM imagery_scene WHERE uri = ?",
            (scene_uri,)
        ).fetchone()
        
        if not row or not row["footprint_geojson"]:
            return 0.0
        
        footprint = json.loads(row["footprint_geojson"])
        footprint_geom = extract_boundary_geometry(footprint)
        boundary_geom = extract_boundary_geometry(boundary_geojson)
        
        if boundary_geom.area == 0:
            return 0.0
        
        if not boundary_geom.intersects(footprint_geom):
            return 0.0
        
        intersection = boundary_geom.intersection(footprint_geom)
        coverage = (intersection.area / boundary_geom.area) * 100.0
        return coverage
        
    except Exception as e:
        print(f"  ⚠️ Error checking footprint coverage: {e}")
        return 0.0


def _find_covering_scenes(
    db_conn,
    target_date: str,
    boundary_geojson: dict,
    min_coverage_percent: float = None,
    max_scenes: int = None,
    max_date_diff_days: float = None,
    prefer_low_cloud: bool = None
) -> List[Tuple[int, str]]:
    """
    Finds scenes from the database that together cover the boundary.
    Returns scenes acquired on or near the target date, preferring low cloud cover.
    
    Args:
        db_conn: SQLite database connection
        target_date: Target acquisition date to match
        boundary_geojson: GeoJSON of the boundary to cover
        min_coverage_percent: Required coverage percentage (default from config)
        max_scenes: Maximum number of scenes to consider (default from config)
        max_date_diff_days: Max days from target date (default from config)
        prefer_low_cloud: Whether to prefer low cloud scenes (default from config)
        
    Returns:
        List of (scene_id, scene_uri) tuples that provide coverage
    """
    from shapely.geometry import shape
    from shapely.ops import unary_union
    import json
    
    # Use config defaults if not specified
    if min_coverage_percent is None:
        min_coverage_percent = COVERAGE_CONFIG["MINIMUM_REQUIRED"]
    if max_scenes is None:
        max_scenes = calculate_max_scenes_needed(boundary_geojson)
    if max_date_diff_days is None:
        max_date_diff_days = TEMPORAL_CONFIG["MAX_DATE_DIFF_DAYS"]
    if prefer_low_cloud is None:
        prefer_low_cloud = SCENE_CONFIG["PREFER_LOW_CLOUD"]
    
    # Get boundary as shapely geometry
    boundary_geom = extract_boundary_geometry(boundary_geojson)
    boundary_area = boundary_geom.area
    
    if boundary_area == 0:
        return []
    
    # Get scenes ordered by proximity to target date AND cloud cover
    query = """
        SELECT id, uri, footprint_geojson, acquired_at, cloud_cover,
               ABS(julianday(acquired_at) - julianday(?)) as date_diff
        FROM imagery_scene
        WHERE footprint_geojson IS NOT NULL
    """
    
    # Filter by cloud cover if configured
    if SCENE_CONFIG["MAX_CLOUD_COVER"] < 100:
        query += f" AND (cloud_cover IS NULL OR cloud_cover <= {SCENE_CONFIG['MAX_CLOUD_COVER']})"
    
    # Order by date proximity and optionally cloud cover
    if prefer_low_cloud:
        query += " ORDER BY date_diff ASC, COALESCE(cloud_cover, 100) ASC"
    else:
        query += " ORDER BY date_diff ASC"
    
    query += " LIMIT ?"
    
    rows = db_conn.execute(
        query,
        (target_date, max_scenes * SCENE_CONFIG["SCENE_SEARCH_MULTIPLIER"])
    ).fetchall()
    
    if not rows:
        return []
    
    selected_scenes = []
    covered_geom = None
    coverage_percent = 0.0
    
    print(f"  Evaluating {len(rows)} candidate scenes...")
    
    for row in rows:
        try:
            row_dict = {k: row[k] for k in row.keys()}
            
            # Check date tolerance
            date_diff = row_dict["date_diff"]
            if date_diff > max_date_diff_days:
                print(f"  ⚠️ Skipping scene {row_dict['uri']} - {date_diff:.0f} days from target (max: {max_date_diff_days:.0f})")
                continue
            
            # Check cloud cover
            cloud_cover = row_dict.get("cloud_cover")
            if cloud_cover and cloud_cover > SCENE_CONFIG["MAX_CLOUD_COVER"]:
                print(f"  ⚠️ Skipping scene {row_dict['uri']} - cloud cover {cloud_cover:.1f}% (max: {SCENE_CONFIG['MAX_CLOUD_COVER']:.1f}%)")
                continue
            
            footprint = json.loads(row_dict["footprint_geojson"])
            footprint_geom = extract_boundary_geometry(footprint)
            
            # Check if this scene intersects our boundary
            if not boundary_geom.intersects(footprint_geom):
                continue
            
            scene_contribution = boundary_geom.intersection(footprint_geom)
            
            if covered_geom is None:
                # First scene
                covered_geom = scene_contribution
                selected_scenes.append((row_dict["id"], row_dict["uri"]))
            else:
                # Check if this scene adds new coverage
                new_coverage = scene_contribution.difference(covered_geom)
                if not new_coverage.is_empty and new_coverage.area > 0:
                    covered_geom = unary_union([covered_geom, scene_contribution])
                    selected_scenes.append((row_dict["id"], row_dict["uri"]))
            
            # Calculate current coverage
            coverage_percent = (covered_geom.area / boundary_area) * 100.0
            
            if coverage_percent >= min_coverage_percent:
                break
            
            if len(selected_scenes) >= max_scenes:
                break
                
        except Exception as e:
            try:
                scene_id = row["id"]
            except Exception:
                scene_id = "unknown"
            print(f"  ⚠️ Error processing scene {scene_id}: {e}")
            continue
    
    print(f"  Found {len(selected_scenes)} scene(s) providing {coverage_percent:.1f}% coverage")
    return selected_scenes


def _download_and_mosaic_bands(
    scene_uris: List[str],
    required_bands: List[str],
    boundary_geojson: dict,
    output_prefix: str
) -> Dict[str, str]:
    """
    Downloads bands from multiple scenes and creates mosaics if needed.
    
    Args:
        scene_uris: List of STAC item URIs to download from
        required_bands: List of band names to download
        boundary_geojson: Boundary for clipping
        output_prefix: Prefix for mosaic output files
        
    Returns:
        Dict mapping band names to file paths (either single files or mosaics)
    """
    if len(scene_uris) == 1:
        # Single scene - just download normally
        result = download_sentinel2_bands_with_validation(
            scene_uris[0],
            required_bands,
            boundary_geojson=boundary_geojson,
            min_coverage_percent=80.0
        )
        return result.paths
    
    # Multiple scenes - download all and mosaic
    print(f"  Downloading bands from {len(scene_uris)} scenes for mosaicking...")
    
    # Collect paths by band
    band_paths: Dict[str, List[str]] = {band: [] for band in required_bands}
    
    for uri in scene_uris:
        paths = download_sentinel2_bands(uri, required_bands)
        for band, path in paths.items():
            band_paths[band].append(path)
    
    # Create mosaics for each band
    print(f"  Creating mosaics for {len(required_bands)} bands...")
    mosaic_results = create_band_mosaic_set(
        band_paths,
        output_prefix,
        boundary_geojson=boundary_geojson
    )
    
    # Return paths to mosaic files with validation
    output_paths = {}
    for band, result in mosaic_results.items():
        if result.success and result.output_path:
            # Validate mosaic coverage if configured
            if VALIDATION_CONFIG["VALIDATE_POST_MOSAIC"]:
                if not result.coverage_result.is_valid:
                    raise MosaicError(
                        f"Mosaic for {band} has insufficient coverage: "
                        f"{result.coverage_result.coverage_percent:.1f}% "
                        f"(required: {COVERAGE_CONFIG['MINIMUM_REQUIRED']}%)",
                        band_name=band,
                        scene_count=len(band_paths[band])
                    )
            output_paths[band] = result.output_path
        else:
            # Don't silently fall back - raise error
            raise MosaicError(
                f"Failed to create mosaic for band {band}: {result.message}",
                band_name=band,
                scene_count=len(band_paths[band])
            )
    
    return output_paths


def run_analysis(
    *,
    mine_area: Optional[dict[str, Any]],
    baseline_date: Optional[str],
    latest_date: Optional[str],
    baseline_scene: Optional[ImageryScene] = None,
    latest_scene: Optional[ImageryScene] = None,
    run_id: Optional[int] = None,
    save_indices: bool = True,
    db_conn = None,
) -> tuple[list[Zone], list[Alert]]:
    """
    Production wrapper around run_analysis_core.
    Validates DB requirement and delegates scientific processing to run_analysis_core.
    """
    if VALIDATION_CONFIG["REQUIRE_DB_CONN"] and db_conn is None:
        raise DatabaseConnectionError(
            "Database connection required for production analysis. "
            "Set VALIDATION_CONFIG['REQUIRE_DB_CONN'] = False for testing only."
        )
    if mine_area is None:
        raise AnalysisError("Mine area configuration is required for analysis", stage="initialization", run_id=run_id)
    if baseline_scene is None or latest_scene is None:
        raise AnalysisError("Both baseline and latest scenes are required", stage="initialization", run_id=run_id)
    if baseline_scene.uri == latest_scene.uri:
        raise IdenticalScenesError(scene_uri=baseline_scene.uri, acquired_at=baseline_scene.acquired_at)

    # Build candidate scenes from DB for epoch grouping
    candidates: List[Dict[str, Any]] = []
    if db_conn is not None:
        rows = db_conn.execute(
            "SELECT id, uri, acquired_at, cloud_cover, footprint_geojson FROM imagery_scene ORDER BY acquired_at DESC LIMIT 50"
        ).fetchall()
        for r in rows:
            row_dict = {k: r[k] for k in r.keys()}
            candidates.append(
                {
                    "id": int(row_dict["id"]),
                    "uri": row_dict["uri"],
                    "acquired_at": row_dict["acquired_at"],
                    "cloud_cover": float(row_dict["cloud_cover"]) if row_dict["cloud_cover"] is not None else None,
                    "footprint_geojson": row_dict["footprint_geojson"],
                }
            )

    result = run_analysis_core(
        mine_area=mine_area,
        baseline_scene=baseline_scene,
        latest_scene=latest_scene,
        candidate_scenes=candidates,
        save_indices=save_indices,
        run_id=run_id,
    )
    zones: list[Zone] = result["zones"]
    alerts: list[Alert] = result["alerts"]
    return zones, alerts


def run_analysis_core(
    *,
    mine_area: dict[str, Any],
    baseline_scene: Optional[ImageryScene] = None,
    latest_scene: Optional[ImageryScene] = None,
    candidate_scenes: Optional[List[Dict[str, Any]]] = None,
    required_bands: Optional[List[str]] = None,
    epoch_tolerance_minutes: float = 10.0,
    min_epoch_coverage_percent: float = 80.0,
    save_indices: bool = True,
    run_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Pure processing function for scientific analysis (no DB access, no side effects beyond optional previews).
    Performs epoch selection, download/mosaic, clipping/resampling, index calculation, and change detection.
    Returns a structured result with zones, alerts, stats, metadata, and epoch_info.
    """
    if required_bands is None:
        required_bands = ["B02", "B03", "B04", "B08", "B11"]
    geometry = mine_area.get("boundary")
    if not geometry:
        raise AnalysisError("No boundary geometry found in mine_area", stage="initialization", run_id=run_id)

    if baseline_scene and latest_scene and baseline_scene.uri == latest_scene.uri:
        raise IdenticalScenesError(scene_uri=baseline_scene.uri, acquired_at=baseline_scene.acquired_at)

    # Decide single-scene vs epoch-based path
    baseline_paths: Dict[str, str] = {}
    latest_paths: Dict[str, str] = {}
    epoch_info: Dict[str, Any] = {}

    def footprint_coverage_for_uri(uri: str) -> float:
        try:
            from backend.utils.stac_downloader import get_scene_footprint
            fp = get_scene_footprint(uri)
            if not fp:
                return 0.0
            boundary_geom = extract_boundary_geometry(geometry)
            footprint_geom = extract_boundary_geometry(fp)
            if not boundary_geom.intersects(footprint_geom):
                return 0.0
            intersection = boundary_geom.intersection(footprint_geom)
            return (intersection.area / boundary_geom.area) * 100.0
        except Exception:
            return 0.0

    baseline_cov = footprint_coverage_for_uri(baseline_scene.uri) if baseline_scene else 0.0
    latest_cov = footprint_coverage_for_uri(latest_scene.uri) if latest_scene else 0.0

    needs_epoch = (baseline_cov < 92.0) or (latest_cov < 92.0)

    print(f"\n=== CORE ANALYSIS ===")
    print(f"Boundary present: {geometry is not None}")
    print(f"Baseline URI: {baseline_scene.uri if baseline_scene else 'None'} (cov ~ {baseline_cov:.1f}%)")
    print(f"Latest URI:   {latest_scene.uri if latest_scene else 'None'} (cov ~ {latest_cov:.1f}%)")

    if needs_epoch:
        print(f"\n[Stage 1] Epoch Selection & Mosaicking")
        from backend.utils.temporal_grouping import build_coverage_sets_from_candidates, select_latest_two_sets
        if not candidate_scenes or len(candidate_scenes) == 0:
            raise InsufficientCoverageError(
                "Insufficient data to build temporal epochs (no candidate scenes provided)",
                coverage_percent=max(baseline_cov, latest_cov),
                required_percent=95.0,
                scene_count=0
            )
        coverage_sets = build_coverage_sets_from_candidates(geometry, candidate_scenes)
        if len(coverage_sets) < 2:
            raise InsufficientCoverageError(
                "Insufficient complete temporal coverage sets",
                coverage_percent=max(baseline_cov, latest_cov),
                required_percent=95.0,
                scene_count=len(coverage_sets)
            )
        latest_set, baseline_set = select_latest_two_sets(coverage_sets)
        epoch_info = {
            "latest": {"epoch_time": latest_set.epoch_time, "coverage_percent": latest_set.coverage_percent, "scene_uris": latest_set.scene_uris},
            "baseline": {"epoch_time": baseline_set.epoch_time, "coverage_percent": baseline_set.coverage_percent, "scene_uris": baseline_set.scene_uris},
        }
        print(f"  Selected epochs:")
        print(f"    Latest:   {epoch_info['latest']['epoch_time']} ({epoch_info['latest']['coverage_percent']:.1f}%) with {len(latest_set.scene_uris)} scenes")
        print(f"    Baseline: {epoch_info['baseline']['epoch_time']} ({epoch_info['baseline']['coverage_percent']:.1f}%) with {len(baseline_set.scene_uris)} scenes")
        baseline_paths = _download_and_mosaic_bands(
            baseline_set.scene_uris, required_bands, geometry, output_prefix=f"run{run_id}_baseline" if run_id else "baseline"
        )
        print(f"  ✓ Baseline mosaic ready")
        latest_paths = _download_and_mosaic_bands(
            latest_set.scene_uris, required_bands, geometry, output_prefix=f"run{run_id}_latest" if run_id else "latest"
        )
        print(f"  ✓ Latest mosaic ready")
    else:
        # Single-scene fast path
        print(f"\n[Stage 1] Single-Scene Download")
        if not baseline_scene or not latest_scene:
            raise AnalysisError("Baseline and latest scenes required for single-scene analysis", stage="validation", run_id=run_id)
        baseline_result = download_sentinel2_bands_with_validation(
            baseline_scene.uri, required_bands, boundary_geojson=geometry, min_coverage_percent=80.0
        )
        latest_result = download_sentinel2_bands_with_validation(
            latest_scene.uri, required_bands, boundary_geojson=geometry, min_coverage_percent=80.0
        )
        baseline_paths = baseline_result.paths
        latest_paths = latest_result.paths
        print(f"  ✓ Baseline and latest bands downloaded")
        epoch_info = {
            "latest": {"epoch_time": latest_scene.acquired_at, "coverage_percent": latest_cov, "scene_uris": [latest_scene.uri]},
            "baseline": {"epoch_time": baseline_scene.acquired_at if baseline_scene else None, "coverage_percent": baseline_cov, "scene_uris": [baseline_scene.uri] if baseline_scene else []},
        }

    # Clip & resample
    print(f"\n[Stage 2] Clip & Resample")
    b_red, transform, b_crs = clip_raster_to_geometry(baseline_paths["B04"], geometry)
    target_shape = b_red.shape
    b_nir, _, _ = clip_raster_to_geometry(baseline_paths["B08"], geometry, target_shape, transform)
    b_green, _, _ = clip_raster_to_geometry(baseline_paths["B03"], geometry, target_shape, transform)
    b_blue, _, _ = clip_raster_to_geometry(baseline_paths["B02"], geometry, target_shape, transform)
    b_swir, _, _ = clip_raster_to_geometry(baseline_paths["B11"], geometry, target_shape, transform)
    print(f"  ✓ Baseline clipped, target shape {target_shape}")

    l_red, _, _ = clip_raster_to_geometry(latest_paths["B04"], geometry, target_shape, transform)
    l_nir, _, _ = clip_raster_to_geometry(latest_paths["B08"], geometry, target_shape, transform)
    l_green, _, _ = clip_raster_to_geometry(latest_paths["B03"], geometry, target_shape, transform)
    l_blue, _, _ = clip_raster_to_geometry(latest_paths["B02"], geometry, target_shape, transform)
    l_swir, _, _ = clip_raster_to_geometry(latest_paths["B11"], geometry, target_shape, transform)
    print(f"  ✓ Latest clipped")

    # Indices
    print(f"\n[Stage 3] Index Calculation")
    b_ndvi = calculate_ndvi(b_red, b_nir)
    b_ndwi = calculate_ndwi(b_green, b_nir)
    b_bsi = calculate_bsi(b_red, b_blue, b_nir, b_swir)
    l_ndvi = calculate_ndvi(l_red, l_nir)
    l_ndwi = calculate_ndwi(l_green, l_nir)
    l_bsi = calculate_bsi(l_red, l_blue, l_nir, l_swir)
    print(f"  ✓ Indices computed")

    # Save previews optionally
    if save_indices:
        print(f"\n[Stage 4] Previews & Change Layers")
        generate_index(b_ndvi, transform, b_crs, 'ndvi', run_id, 'baseline')
        generate_index(b_ndwi, transform, b_crs, 'ndwi', run_id, 'baseline')
        generate_index(b_bsi, transform, b_crs, 'bsi', run_id, 'baseline')
        generate_index(l_ndvi, transform, b_crs, 'ndvi', run_id, 'latest')
        generate_index(l_ndwi, transform, b_crs, 'ndwi', run_id, 'latest')
        generate_index(l_bsi, transform, b_crs, 'bsi', run_id, 'latest')
        generate_change_preview(b_ndvi, l_ndvi, transform, b_crs, 'ndvi', run_id)
        generate_change_preview(b_ndwi, l_ndwi, transform, b_crs, 'ndwi', run_id)
        generate_change_preview(b_bsi, l_bsi, transform, b_crs, 'bsi', run_id)
        print(f"  ✓ Previews generated")

    # Change Detection & Zones
    print(f"\n[Stage 5] Change Detection & Zones")
    zones: list[Zone] = []
    veg_loss_mask = (b_ndvi - l_ndvi) > 0.15
    mining_mask = (l_bsi - b_bsi) > 0.25
    water_mask = (l_ndwi - b_ndwi) > 0.20

    def add_zones(mask: np.ndarray, zone_type: str):
        polys = vectorize_mask(mask, transform, b_crs)
        for poly in polys:
            area_ha = _calculate_area(poly["geometry"])
            zones.append(Zone(zone_type=zone_type, area_ha=area_ha, geometry=poly["geometry"]))

    add_zones(veg_loss_mask, "vegetation_loss")
    add_zones(mining_mask, "mining_expansion")
    add_zones(water_mask, "water_accumulation")
    print(f"  ✓ Zones extracted: {len(zones)}")

    # Alerts
    from backend.alert_rules import AlertRuleEngine
    alert_engine = AlertRuleEngine()
    context = {"mine_area": mine_area, "baseline_date": baseline_scene.acquired_at if baseline_scene else None, "latest_date": latest_scene.acquired_at if latest_scene else None}
    alerts = alert_engine.evaluate_zones(zones, context)
    print(f"  ✓ Alerts generated: {len(alerts)}")

    # Stats
    stats: Dict[str, Any] = {}
    for z in zones:
        stats.setdefault(z.zone_type, {"count": 0, "area_ha": 0.0})
        stats[z.zone_type]["count"] += 1
        stats[z.zone_type]["area_ha"] += z.area_ha
    print(f"\n=== CORE ANALYSIS COMPLETE ===")

    metadata = {
        "required_bands": required_bands,
        "baseline_paths": baseline_paths,
        "latest_paths": latest_paths,
    }

    return {
        "zones": zones,
        "alerts": alerts,
        "stats": stats,
        "metadata": metadata,
        "epoch_info": epoch_info,
    }

def _calculate_area(geometry: dict) -> float:
    """Estimates area in hectares from GeoJSON geometry."""
    try:
        from shapely.geometry import shape
        import pyproj
        from shapely.ops import transform
        
        s = shape(geometry)
        lon, lat = s.centroid.x, s.centroid.y
        utm_zone = int((lon + 180) / 6) + 1
        proj_str = f"+proj=utm +zone={utm_zone} +datum=WGS84 +units=m +no_defs"
        project = pyproj.Transformer.from_crs("EPSG:4326", proj_str, always_xy=True).transform
        s_utm = transform(project, s)
        return s_utm.area / 10000.0 # m^2 to ha
    except Exception as e:
        print(f"Area calculation error: {e}")
        # Very rough fallback
        return 0.0
