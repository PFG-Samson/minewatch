import numpy as np
import rasterio
from PIL import Image
from pathlib import Path
from typing import List, Dict, Any
from backend.utils.spatial import get_raster_bounds_4326

# Output directory for processed PNGs
CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"

def ensure_cache_dir():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

def generate_rgb_png(
    red_path: str, 
    green_path: str, 
    blue_path: str, 
    output_name: str,
    brightness: float = 2.5
) -> Dict[str, Any]:
    """
    Creates a true-color PNG from 16-bit Sentinel-2 bands.
    Returns metadata including bounds for Leaflet.
    """
    ensure_cache_dir()
    output_path = CACHE_DIR / f"{output_name}.png"
    
    if not output_path.exists():
        with rasterio.open(red_path) as r_src:
            r = r_src.read(1)
        with rasterio.open(green_path) as g_src:
            g = g_src.read(1)
        with rasterio.open(blue_path) as b_src:
            b = b_src.read(1)

        def normalize(band):
            band = band.astype(float)
            # Sentinel-2 usually has valid reflectance up to 10000.
            # 3000 is a common 'bright' limit for visual contrast.
            band = (band / 3000.0) * 255.0 * brightness
            return np.clip(band, 0, 255).astype(np.uint8)

        rgb = np.stack([normalize(r), normalize(g), normalize(b)], axis=-1)
        img = Image.fromarray(rgb)
        img.save(output_path)

    bounds = get_raster_bounds_4326(red_path)
    
    return {
        "url": f"/data/cache/{output_name}.png",
        "bounds": bounds
    }

def generate_single_band_png(
    band_path: str,
    output_name: str,
    colormap: str = "viridis"
) -> Dict[str, Any]:
    """Generates a grayscale or colormapped PNG for single indices (like NDVI)."""
    ensure_cache_dir()
    output_path = CACHE_DIR / f"{output_name}.png"
    
    # Simple grayscale for now. Could add matplotlib colormaps later.
    if not output_path.exists():
        with rasterio.open(band_path) as src:
            data = src.read(1)
            
        # Assuming data is already normalized or in a known range (e.g. -1 to 1 for NDVI)
        # For raw bands, we scale. For NDVI, we handle specifically.
        if "ndvi" in output_name.lower():
            # Map -1..1 to 0..255
            data = ((data + 1.0) / 2.0) * 255.0
        else:
            data = (data / 3000.0) * 255.0
            
        data = np.clip(data, 0, 255).astype(np.uint8)
        img = Image.fromarray(data)
        img.save(output_path)

    bounds = get_raster_bounds_4326(band_path)
    
    return {
        "url": f"/data/cache/{output_name}.png",
        "bounds": bounds
    }
