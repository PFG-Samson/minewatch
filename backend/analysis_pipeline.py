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
            # Check date tolerance
            date_diff = row["date_diff"]
            if date_diff > max_date_diff_days:
                print(f"  ⚠️ Skipping scene {row['uri']} - {date_diff:.0f} days from target (max: {max_date_diff_days:.0f})")
                continue
            
            # Check cloud cover
            cloud_cover = row.get("cloud_cover")
            if cloud_cover and cloud_cover > SCENE_CONFIG["MAX_CLOUD_COVER"]:
                print(f"  ⚠️ Skipping scene {row['uri']} - cloud cover {cloud_cover:.1f}% (max: {SCENE_CONFIG['MAX_CLOUD_COVER']:.1f}%)")
                continue
            
            footprint = json.loads(row["footprint_geojson"])
            footprint_geom = extract_boundary_geometry(footprint)
            
            # Check if this scene intersects our boundary
            if not boundary_geom.intersects(footprint_geom):
                continue
            
            scene_contribution = boundary_geom.intersection(footprint_geom)
            
            if covered_geom is None:
                # First scene
                covered_geom = scene_contribution
                selected_scenes.append((row["id"], row["uri"]))
            else:
                # Check if this scene adds new coverage
                new_coverage = scene_contribution.difference(covered_geom)
                if not new_coverage.is_empty and new_coverage.area > 0:
                    covered_geom = unary_union([covered_geom, scene_contribution])
                    selected_scenes.append((row["id"], row["uri"]))
            
            # Calculate current coverage
            coverage_percent = (covered_geom.area / boundary_area) * 100.0
            
            if coverage_percent >= min_coverage_percent:
                break
            
            if len(selected_scenes) >= max_scenes:
                break
                
        except Exception as e:
            print(f"  ⚠️ Error processing scene {row['id']}: {e}")
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
    Runs the full analysis pipeline with coverage validation and index generation.
    Automatically mosaics multiple scenes when a single scene doesn't cover the full boundary.
    
    Args:
        mine_area: Mine area configuration with boundary
        baseline_date: Date string for baseline
        latest_date: Date string for latest
        baseline_scene: Baseline imagery scene
        latest_scene: Latest imagery scene
        run_id: Analysis run ID for saving outputs
        save_indices: Whether to save index GeoTIFFs and previews
        db_conn: Database connection for finding additional scenes (REQUIRED in production)
    
    Returns:
        Tuple of (zones, alerts)
        
    Raises:
        DatabaseConnectionError: If db_conn is None and REQUIRE_DB_CONN is True
        IdenticalScenesError: If baseline and latest scenes are the same
        InsufficientCoverageError: If coverage is below minimum threshold
        AnalysisError: For other unrecoverable errors
    """
    # PHASE 1: Early Validation
    print(f"\n{'='*60}")
    print(f"ANALYSIS PIPELINE - Validation")
    print(f"{'='*60}")
    
    # Require database connection for production
    if VALIDATION_CONFIG["REQUIRE_DB_CONN"] and db_conn is None:
        raise DatabaseConnectionError(
            "Database connection required for production analysis. "
            "Set VALIDATION_CONFIG['REQUIRE_DB_CONN'] = False for testing only."
        )
    
    # Check for required data
    if baseline_scene is None or latest_scene is None or mine_area is None:
        raise AnalysisError(
            "Insufficient data for analysis",
            stage="validation",
            run_id=run_id
        )
    
    # CRITICAL: Check for identical scenes EARLY (before any processing)
    if baseline_scene.uri == latest_scene.uri:
        raise IdenticalScenesError(
            scene_uri=baseline_scene.uri,
            acquired_at=baseline_scene.acquired_at
        )

    print(f"  ✓ Validation passed")
    print(f"  Baseline: {baseline_scene.uri}")
    print(f"  Latest: {latest_scene.uri}")
    
    try:
        # 1. Prepare required bands
        # NDVI: Red (B04), NIR (B08)
        # NDWI: Green (B03), NIR (B08)
        # BSI: Red (B04), Blue (B02), NIR (B08), SWIR1 (B11)
        required_bands = ["B02", "B03", "B04", "B08", "B11"]
        
        print(f"\n{'='*60}")
        print(f"ANALYSIS PIPELINE - {mine_area.get('name', 'Mine')}")
        print(f"{'='*60}")
        if run_id:
            print(f"Run ID: {run_id}")
        print(f"Required bands: {', '.join(required_bands)}")
        
        geometry = mine_area.get("boundary")
        if not geometry:
            raise AnalysisError(
                "No boundary geometry found in mine_area",
                stage="initialization",
                run_id=run_id
            )

        # 2. Download bands with coverage validation and multi-scene support
        print(f"\n--- STAGE 1: Coverage Check & Download ---")
        
        # Check footprint coverage BEFORE downloading (uses actual data extent from STAC)
        # This is more accurate than post-download bounds checking
        baseline_footprint_coverage = 0.0
        latest_footprint_coverage = 0.0
        
        if db_conn is not None:
            print(f"\nChecking scene footprint coverage...")
            baseline_footprint_coverage = _check_scene_footprint_coverage(
                db_conn, baseline_scene.uri, geometry
            )
            latest_footprint_coverage = _check_scene_footprint_coverage(
                db_conn, latest_scene.uri, geometry
            )
            print(f"  Baseline scene footprint coverage: {baseline_footprint_coverage:.1f}%")
            print(f"  Latest scene footprint coverage: {latest_footprint_coverage:.1f}%")
        
        # Determine if we need multiple scenes for baseline
        baseline_needs_mosaic = baseline_footprint_coverage < COVERAGE_CONFIG["MOSAIC_THRESHOLD"]
        
        if baseline_needs_mosaic and db_conn is None:
            # Can't mosaic without database
            if VALIDATION_CONFIG["FAIL_ON_INSUFFICIENT_COVERAGE"]:
                raise InsufficientCoverageError(
                    f"Baseline scene has insufficient coverage and no database connection for mosaicking",
                    coverage_percent=baseline_footprint_coverage,
                    required_percent=COVERAGE_CONFIG["MINIMUM_REQUIRED"],
                    scene_count=1
                )
            else:
                print(f"  ⚠️ WARNING: Baseline coverage {baseline_footprint_coverage:.1f}% below threshold")
        
        if baseline_needs_mosaic and db_conn is not None:
            print(f"\n⚠️ Baseline coverage insufficient ({baseline_footprint_coverage:.1f}%)")
            print(f"  → Searching for additional scenes to complete coverage...")
            
            covering_scenes = _find_covering_scenes(
                db_conn,
                baseline_scene.acquired_at,
                geometry,
                min_coverage_percent=95.0,
                max_scenes=4
            )
            
            if len(covering_scenes) > 1:
                scene_uris = [uri for _, uri in covering_scenes]
                print(f"  Downloading and mosaicking {len(scene_uris)} scenes for baseline...")
                baseline_paths = _download_and_mosaic_bands(
                    scene_uris,
                    required_bands,
                    geometry,
                    output_prefix=f"run{run_id}_baseline" if run_id else "baseline"
                )
                print(f"  ✓ Created baseline mosaic from {len(scene_uris)} scenes")
            else:
                print(f"  ⚠️ Only 1 scene available - validating single scene coverage...")
                
                # Check if single scene meets minimum requirements
                if baseline_footprint_coverage < COVERAGE_CONFIG["MINIMUM_REQUIRED"]:
                    if VALIDATION_CONFIG["FAIL_ON_INSUFFICIENT_COVERAGE"]:
                        raise InsufficientCoverageError(
                            f"Single baseline scene provides insufficient coverage",
                            coverage_percent=baseline_footprint_coverage,
                            required_percent=COVERAGE_CONFIG["MINIMUM_REQUIRED"],
                            scene_count=1,
                            metadata={
                                "scene_uri": baseline_scene.uri,
                                "acquired_at": baseline_scene.acquired_at
                            }
                        )
                    else:
                        print(f"  ⚠️ WARNING: Single scene coverage {baseline_footprint_coverage:.1f}% below minimum")
                
                baseline_result = download_sentinel2_bands_with_validation(
                    baseline_scene.uri, required_bands,
                    boundary_geojson=geometry, min_coverage_percent=COVERAGE_CONFIG["DOWNLOAD_MINIMUM"]
                )
                baseline_paths = baseline_result.paths
        else:
            print(f"\nDownloading baseline scene bands...")
            baseline_result = download_sentinel2_bands_with_validation(
                baseline_scene.uri, required_bands,
                boundary_geojson=geometry, min_coverage_percent=COVERAGE_CONFIG["DOWNLOAD_MINIMUM"]
            )
            baseline_paths = baseline_result.paths
            if baseline_footprint_coverage >= COVERAGE_CONFIG["MOSAIC_THRESHOLD"]:
                print(f"  ✓ Single scene provides {baseline_footprint_coverage:.1f}% coverage")
        
        # Determine if we need multiple scenes for latest
        latest_needs_mosaic = latest_footprint_coverage < COVERAGE_CONFIG["MOSAIC_THRESHOLD"]
        
        if latest_needs_mosaic and db_conn is None:
            # Can't mosaic without database
            if VALIDATION_CONFIG["FAIL_ON_INSUFFICIENT_COVERAGE"]:
                raise InsufficientCoverageError(
                    f"Latest scene has insufficient coverage and no database connection for mosaicking",
                    coverage_percent=latest_footprint_coverage,
                    required_percent=COVERAGE_CONFIG["MINIMUM_REQUIRED"],
                    scene_count=1
                )
            else:
                print(f"  ⚠️ WARNING: Latest coverage {latest_footprint_coverage:.1f}% below threshold")
        
        if latest_needs_mosaic and db_conn is not None:
            print(f"\n⚠️ Latest coverage insufficient ({latest_footprint_coverage:.1f}%)")
            print(f"  → Searching for additional scenes to complete coverage...")
            
            covering_scenes = _find_covering_scenes(
                db_conn,
                latest_scene.acquired_at,
                geometry,
                min_coverage_percent=95.0,
                max_scenes=4
            )
            
            if len(covering_scenes) > 1:
                scene_uris = [uri for _, uri in covering_scenes]
                print(f"  Downloading and mosaicking {len(scene_uris)} scenes for latest...")
                latest_paths = _download_and_mosaic_bands(
                    scene_uris,
                    required_bands,
                    geometry,
                    output_prefix=f"run{run_id}_latest" if run_id else "latest"
                )
                print(f"  ✓ Created latest mosaic from {len(scene_uris)} scenes")
            else:
                print(f"  ⚠️ Only 1 scene available - validating single scene coverage...")
                
                # Check if single scene meets minimum requirements
                if latest_footprint_coverage < COVERAGE_CONFIG["MINIMUM_REQUIRED"]:
                    if VALIDATION_CONFIG["FAIL_ON_INSUFFICIENT_COVERAGE"]:
                        raise InsufficientCoverageError(
                            f"Single latest scene provides insufficient coverage",
                            coverage_percent=latest_footprint_coverage,
                            required_percent=COVERAGE_CONFIG["MINIMUM_REQUIRED"],
                            scene_count=1,
                            metadata={
                                "scene_uri": latest_scene.uri,
                                "acquired_at": latest_scene.acquired_at
                            }
                        )
                    else:
                        print(f"  ⚠️ WARNING: Single scene coverage {latest_footprint_coverage:.1f}% below minimum")
                
                latest_result = download_sentinel2_bands_with_validation(
                    latest_scene.uri, required_bands,
                    boundary_geojson=geometry, min_coverage_percent=COVERAGE_CONFIG["DOWNLOAD_MINIMUM"]
                )
                latest_paths = latest_result.paths
        else:
            print(f"\nDownloading latest scene bands...")
            latest_result = download_sentinel2_bands_with_validation(
                latest_scene.uri, required_bands,
                boundary_geojson=geometry, min_coverage_percent=COVERAGE_CONFIG["DOWNLOAD_MINIMUM"]
            )
            latest_paths = latest_result.paths
            if latest_footprint_coverage >= COVERAGE_CONFIG["MOSAIC_THRESHOLD"]:
                print(f"  ✓ Single scene provides {latest_footprint_coverage:.1f}% coverage")

        # 3. Process Baseline
        print(f"\n--- STAGE 2: Clip & Resample ---")
        print(f"Processing baseline scene...")
        
        b_red, transform, b_crs = clip_raster_to_geometry(baseline_paths["B04"], geometry)
        target_shape = b_red.shape
        print(f"  Target shape: {target_shape}")
        
        b_nir, _, _ = clip_raster_to_geometry(baseline_paths["B08"], geometry, target_shape, transform)
        b_green, _, _ = clip_raster_to_geometry(baseline_paths["B03"], geometry, target_shape, transform)
        b_blue, _, _ = clip_raster_to_geometry(baseline_paths["B02"], geometry, target_shape, transform)
        b_swir, _, _ = clip_raster_to_geometry(baseline_paths["B11"], geometry, target_shape, transform)
        print(f"  ✓ Baseline bands clipped")

        # 4. Process Latest
        print(f"\nProcessing latest scene...")
        l_red, _, _ = clip_raster_to_geometry(latest_paths["B04"], geometry, target_shape, transform)
        l_nir, _, _ = clip_raster_to_geometry(latest_paths["B08"], geometry, target_shape, transform)
        l_green, _, _ = clip_raster_to_geometry(latest_paths["B03"], geometry, target_shape, transform)
        l_blue, _, _ = clip_raster_to_geometry(latest_paths["B02"], geometry, target_shape, transform)
        l_swir, _, _ = clip_raster_to_geometry(latest_paths["B11"], geometry, target_shape, transform)
        print(f"  ✓ Latest bands clipped")

        # 5. Calculate Indices
        print(f"\n--- STAGE 3: Index Calculation ---")
        
        print(f"Calculating baseline indices...")
        b_ndvi = calculate_ndvi(b_red, b_nir)
        b_ndwi = calculate_ndwi(b_green, b_nir)
        b_bsi = calculate_bsi(b_red, b_blue, b_nir, b_swir)
        print(f"  NDVI: min={b_ndvi.min():.3f}, max={b_ndvi.max():.3f}, mean={b_ndvi.mean():.3f}")
        print(f"  NDWI: min={b_ndwi.min():.3f}, max={b_ndwi.max():.3f}, mean={b_ndwi.mean():.3f}")
        print(f"  BSI:  min={b_bsi.min():.3f}, max={b_bsi.max():.3f}, mean={b_bsi.mean():.3f}")

        print(f"\nCalculating latest indices...")
        l_ndvi = calculate_ndvi(l_red, l_nir)
        l_ndwi = calculate_ndwi(l_green, l_nir)
        l_bsi = calculate_bsi(l_red, l_blue, l_nir, l_swir)
        print(f"  NDVI: min={l_ndvi.min():.3f}, max={l_ndvi.max():.3f}, mean={l_ndvi.mean():.3f}")
        print(f"  NDWI: min={l_ndwi.min():.3f}, max={l_ndwi.max():.3f}, mean={l_ndwi.mean():.3f}")
        print(f"  BSI:  min={l_bsi.min():.3f}, max={l_bsi.max():.3f}, mean={l_bsi.mean():.3f}")

        # 6. Save indices and generate previews
        if save_indices and run_id:
            print(f"\n--- STAGE 4: Save Indices & Generate Previews ---")
            
            # Baseline indices
            print(f"Saving baseline indices...")
            baseline_ndvi_result = generate_index(b_ndvi, transform, b_crs, 'ndvi', run_id, 'baseline')
            baseline_ndwi_result = generate_index(b_ndwi, transform, b_crs, 'ndwi', run_id, 'baseline')
            baseline_bsi_result = generate_index(b_bsi, transform, b_crs, 'bsi', run_id, 'baseline')
            print(f"  ✓ Baseline NDVI: {baseline_ndvi_result.preview_url}")
            print(f"  ✓ Baseline NDWI: {baseline_ndwi_result.preview_url}")
            print(f"  ✓ Baseline BSI: {baseline_bsi_result.preview_url}")
            
            # Latest indices
            print(f"\nSaving latest indices...")
            latest_ndvi_result = generate_index(l_ndvi, transform, b_crs, 'ndvi', run_id, 'latest')
            latest_ndwi_result = generate_index(l_ndwi, transform, b_crs, 'ndwi', run_id, 'latest')
            latest_bsi_result = generate_index(l_bsi, transform, b_crs, 'bsi', run_id, 'latest')
            print(f"  ✓ Latest NDVI: {latest_ndvi_result.preview_url}")
            print(f"  ✓ Latest NDWI: {latest_ndwi_result.preview_url}")
            print(f"  ✓ Latest BSI: {latest_bsi_result.preview_url}")
            
            # Change layers
            print(f"\nGenerating change detection layers...")
            ndvi_change = generate_change_preview(b_ndvi, l_ndvi, transform, b_crs, 'ndvi', run_id)
            ndwi_change = generate_change_preview(b_ndwi, l_ndwi, transform, b_crs, 'ndwi', run_id)
            bsi_change = generate_change_preview(b_bsi, l_bsi, transform, b_crs, 'bsi', run_id)
            print(f"  ✓ NDVI Change: {ndvi_change.preview_url}")
            print(f"  ✓ NDWI Change: {ndwi_change.preview_url}")
            print(f"  ✓ BSI Change: {bsi_change.preview_url}")

        # 7. Change Detection Logic
        print(f"\n--- STAGE 5: Change Detection & Zone Generation ---")
        zones: list[Zone] = []

        # Vegetation Loss (NDVI drop > 0.15)
        ndvi_diff = l_ndvi - b_ndvi
        veg_loss_mask = (ndvi_diff < -0.15).astype(np.uint8)
        veg_loss_features = vectorize_mask(veg_loss_mask, transform, b_crs)
        veg_loss_count = 0
        for feat in veg_loss_features:
            area = _calculate_area(feat["geometry"])
            if area > 0.1:  # Min 0.1 ha to show up
                zones.append(Zone("vegetation_loss", area, feat["geometry"]))
                veg_loss_count += 1
        print(f"  Vegetation loss zones: {veg_loss_count}")

        # Bare Soil Expansion (BSI increase > 0.1) - Mining Pits
        bsi_diff = l_bsi - b_bsi
        soil_gain_mask = (bsi_diff > 0.1).astype(np.uint8)
        soil_features = vectorize_mask(soil_gain_mask, transform, b_crs)
        mining_count = 0
        for feat in soil_features:
            area = _calculate_area(feat["geometry"])
            if area > 0.1:
                zones.append(Zone("mining_expansion", area, feat["geometry"]))
                mining_count += 1
        print(f"  Mining expansion zones: {mining_count}")

        # Water Change (NDWI delta > 0.2)
        ndwi_diff = l_ndwi - b_ndwi
        water_gain_mask = (ndwi_diff > 0.2).astype(np.uint8)
        water_features = vectorize_mask(water_gain_mask, transform, b_crs)
        water_count = 0
        for feat in water_features:
            area = _calculate_area(feat["geometry"])
            if area > 0.05:
                zones.append(Zone("water_accumulation", area, feat["geometry"]))
                water_count += 1
        print(f"  Water accumulation zones: {water_count}")

        # 8. Generate alerts using rule engine
        print(f"\n--- STAGE 6: Alert Generation ---")
        from backend.alert_rules import AlertRuleEngine
        
        alert_engine = AlertRuleEngine()
        context = {
            "mine_area": mine_area,
            "baseline_date": baseline_date,
            "latest_date": latest_date
        }
        alerts = alert_engine.evaluate_zones(zones, context)
        print(f"  Generated {len(alerts)} alerts")

        print(f"\n{'='*60}")
        print(f"ANALYSIS COMPLETE")
        print(f"  Total zones: {len(zones)}")
        print(f"  Total alerts: {len(alerts)}")
        print(f"{'='*60}\n")
        
        return zones, alerts

    except (InsufficientCoverageError, MosaicError, IdenticalScenesError, 
            DatabaseConnectionError, TemporalInconsistencyError) as e:
        # Re-raise known errors for proper handling
        print(f"\n✗ Analysis failed: {e}")
        raise
    except Exception as e:
        import traceback
        print(f"\n✗ Unexpected error in analysis pipeline: {e}")
        traceback.print_exc()
        # Wrap in AnalysisError for consistent error handling
        raise AnalysisError(
            f"Unexpected error during analysis: {str(e)}",
            stage="unknown",
            run_id=run_id,
            original_error=e
        ) from e

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
