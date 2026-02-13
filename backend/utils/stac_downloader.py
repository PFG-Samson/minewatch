import os
import requests
import pystac
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass

# Base directory for storing downloaded imagery bands
DATA_DIR = Path(__file__).parent.parent / "data" / "imagery"


@dataclass
class DownloadResult:
    """Result of a band download operation with coverage info."""
    paths: Dict[str, str]  # band name -> file path
    coverage_percent: float
    coverage_valid: bool
    message: str


def ensure_data_dir():
    """Ensures the imagery data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def download_sentinel2_bands(stac_item_id: str, bands: List[str]) -> Dict[str, str]:
    """
    Downloads specific bands for a Sentinel-2 STAC item from Planetary Computer.
    Returns a mapping of band name to local file path.
    """
    ensure_data_dir()
    
    # URL for Planetary Computer STAC item retrieval
    # Note: In a production app, we'd use pystac-client to search. 
    # Here we assume we have the item ID and can construct the asset URLs or use the API.
    # For simplicity, we'll use the ID to fetch the item via the PC API.
    
    try:
        item_url = f"https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-2-l2a/items/{stac_item_id}"
        print(f"Fetching STAC item: {item_url}")
        resp = requests.get(item_url, timeout=30)
        resp.raise_for_status()
        item_dict = resp.json()
    except requests.exceptions.RequestException as e:
        print(f"ERROR fetching STAC item {stac_item_id}: {e}")
        raise
    
    downloaded_paths = {}
    assets = item_dict.get("assets", {})
    
    for band in bands:
        if band in assets:
            try:
                asset_url = assets[band]["href"]
                # PC requires signing the URL with proper encoding
                import urllib.parse
                encoded_url = urllib.parse.quote(asset_url, safe='')
                sign_url = f"https://planetarycomputer.microsoft.com/api/sas/v1/sign?href={encoded_url}"
                signed_url_resp = requests.get(sign_url, timeout=30)
                signed_url_resp.raise_for_status()
                signed_url = signed_url_resp.json().get("href", asset_url)
                
                file_name = f"{stac_item_id}_{band}.tif"
                local_path = DATA_DIR / file_name
                
                if not local_path.exists():
                    print(f"Downloading {band} for {stac_item_id}...")
                    with requests.get(signed_url, stream=True, timeout=120) as r:
                        r.raise_for_status()
                        total_size = int(r.headers.get('content-length', 0))
                        print(f"  Size: {total_size / (1024*1024):.1f} MB")
                        with open(local_path, 'wb') as f:
                            downloaded = 0
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
                                downloaded += len(chunk)
                                if downloaded % (1024 * 1024) == 0:  # Log every MB
                                    print(f"  Downloaded: {downloaded / (1024*1024):.1f} MB")
                    print(f"  ✓ {band} download complete")
                else:
                    print(f"  ✓ {band} already cached")
                
                downloaded_paths[band] = str(local_path)
            except Exception as e:
                print(f"ERROR downloading band {band} for {stac_item_id}: {e}")
                raise
        else:
            error_msg = f"Band {band} not found in STAC item {stac_item_id}"
            print(f"ERROR: {error_msg}")
            raise ValueError(error_msg)
            
    return downloaded_paths


def download_sentinel2_bands_with_validation(
    stac_item_id: str, 
    bands: List[str],
    boundary_geojson: Optional[Dict[str, Any]] = None,
    min_coverage_percent: float = 90.0
) -> DownloadResult:
    """
    Downloads bands and validates coverage against the boundary.
    
    Args:
        stac_item_id: STAC item identifier
        bands: List of band names to download
        boundary_geojson: Optional boundary to validate coverage against
        min_coverage_percent: Minimum required coverage percentage
        
    Returns:
        DownloadResult with paths and coverage information
    """
    # Download bands first
    paths = download_sentinel2_bands(stac_item_id, bands)
    
    # If no boundary provided, skip validation
    if boundary_geojson is None:
        return DownloadResult(
            paths=paths,
            coverage_percent=100.0,
            coverage_valid=True,
            message="Downloaded successfully (no boundary validation)"
        )
    
    # Validate coverage using one of the bands (B04 red is common)
    from backend.utils.coverage_validator import validate_coverage
    
    test_band = paths.get('B04') or paths.get(bands[0])
    if not test_band:
        return DownloadResult(
            paths=paths,
            coverage_percent=0.0,
            coverage_valid=False,
            message="No bands downloaded for coverage validation"
        )
    
    coverage_result = validate_coverage(
        test_band,
        boundary_geojson,
        min_coverage_percent=min_coverage_percent,
        check_valid_data=False  # Faster check using bounds only
    )
    
    print(f"  Coverage: {coverage_result.coverage_percent:.1f}% - {coverage_result.message}")
    
    return DownloadResult(
        paths=paths,
        coverage_percent=coverage_result.coverage_percent,
        coverage_valid=coverage_result.is_valid,
        message=coverage_result.message
    )


def get_scene_footprint(stac_item_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches the footprint geometry of a STAC item.
    
    Args:
        stac_item_id: STAC item identifier
        
    Returns:
        GeoJSON geometry of the scene footprint, or None on error
    """
    try:
        item_url = f"https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-2-l2a/items/{stac_item_id}"
        resp = requests.get(item_url, timeout=30)
        resp.raise_for_status()
        item_dict = resp.json()
        return item_dict.get("geometry")
    except Exception as e:
        print(f"Error fetching scene footprint: {e}")
        return None


def find_covering_scenes(
    scene_ids: List[str],
    boundary_geojson: Dict[str, Any],
    min_coverage_percent: float = 95.0
) -> Tuple[List[str], float]:
    """
    Finds the minimum set of scenes needed to cover a boundary.
    
    Args:
        scene_ids: List of available scene IDs
        boundary_geojson: Target boundary
        min_coverage_percent: Required coverage threshold
        
    Returns:
        Tuple of (selected scene IDs, achieved coverage percent)
    """
    from backend.utils.coverage_validator import find_optimal_scenes
    
    # Fetch footprints for all scenes
    scene_footprints = []
    for scene_id in scene_ids:
        footprint = get_scene_footprint(scene_id)
        if footprint:
            scene_footprints.append({
                'id': scene_id,
                'footprint': footprint,
                'cloud_cover': None  # Could fetch this too if needed
            })
    
    if not scene_footprints:
        return [], 0.0
    
    selected_ids = find_optimal_scenes(
        scene_footprints,
        boundary_geojson,
        min_coverage_percent=min_coverage_percent
    )
    
    # Calculate achieved coverage
    if selected_ids:
        from backend.utils.coverage_validator import validate_multi_scene_coverage
        from backend.utils.coverage_validator import extract_boundary_geometry
        from shapely.geometry import shape, mapping
        from shapely.ops import unary_union
        
        selected_footprints = [
            sf['footprint'] for sf in scene_footprints 
            if sf['id'] in selected_ids
        ]
        
        boundary_geom = extract_boundary_geometry(boundary_geojson)
        combined = unary_union([shape(extract_boundary_geometry(fp)) for fp in selected_footprints])
        intersection = boundary_geom.intersection(combined)
        coverage = (intersection.area / boundary_geom.area) * 100.0
        
        return selected_ids, coverage
    
    return [], 0.0
