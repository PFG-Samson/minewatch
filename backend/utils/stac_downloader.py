import os
import requests
import pystac
from typing import Dict, List, Optional
from pathlib import Path

# Base directory for storing downloaded imagery bands
DATA_DIR = Path(__file__).parent.parent / "data" / "imagery"

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
