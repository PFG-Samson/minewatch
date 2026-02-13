"""
Index Generator Module for MineWatch

Saves calculated spectral indices (NDVI, NDWI, BSI) as GeoTIFFs with proper metadata.
Generates colormapped preview PNGs for display in the frontend.
"""

from __future__ import annotations
import numpy as np
import rasterio
from rasterio.transform import Affine
from PIL import Image
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
import colorsys

from backend.utils.spatial import get_raster_bounds_4326


# Output directories
INDEX_DIR = Path(__file__).parent.parent / "data" / "indices"
PREVIEW_DIR = Path(__file__).parent.parent / "data" / "cache"


def ensure_dirs():
    """Ensures output directories exist."""
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class IndexResult:
    """Result of an index generation operation."""
    success: bool
    index_type: str
    geotiff_path: Optional[str]
    preview_path: Optional[str]
    preview_url: Optional[str]
    bounds: Optional[List[float]]  # [min_lat, min_lon, max_lat, max_lon]
    stats: Dict[str, float]  # min, max, mean, std
    message: str


# Color maps for different indices
COLORMAPS = {
    'ndvi': {
        # Brown to Yellow to Green gradient for vegetation
        'colors': [
            (-1.0, (139, 69, 19)),    # Brown - bare/dead
            (-0.2, (210, 180, 140)),   # Tan - sparse
            (0.0, (255, 255, 200)),    # Light yellow - minimal
            (0.2, (200, 230, 150)),    # Yellow-green - moderate
            (0.4, (100, 200, 100)),    # Light green - healthy
            (0.6, (50, 150, 50)),      # Medium green - dense
            (0.8, (0, 100, 0)),        # Dark green - very dense
            (1.0, (0, 60, 0)),         # Deep green - forest
        ],
        'nodata_color': (128, 128, 128),  # Gray for nodata
    },
    'ndwi': {
        # Brown to Blue gradient for water
        'colors': [
            (-1.0, (139, 90, 43)),     # Brown - dry
            (-0.3, (210, 180, 140)),    # Tan
            (0.0, (200, 200, 200)),     # Gray - neutral
            (0.2, (150, 200, 255)),     # Light blue
            (0.4, (100, 150, 255)),     # Medium blue
            (0.6, (50, 100, 220)),      # Blue
            (0.8, (0, 50, 180)),        # Dark blue
            (1.0, (0, 0, 139)),         # Deep blue - water
        ],
        'nodata_color': (128, 128, 128),
    },
    'bsi': {
        # Green to Brown gradient for bare soil
        'colors': [
            (-1.0, (0, 100, 0)),        # Dark green - vegetation
            (-0.3, (100, 180, 100)),    # Light green
            (0.0, (200, 200, 150)),     # Yellow-gray - mixed
            (0.2, (210, 180, 120)),     # Light tan
            (0.4, (180, 140, 80)),      # Tan
            (0.6, (160, 100, 50)),      # Brown
            (0.8, (139, 69, 19)),       # Dark brown
            (1.0, (100, 50, 10)),       # Very dark brown - bare soil
        ],
        'nodata_color': (128, 128, 128),
    },
    'change': {
        # Red to White to Green for change detection
        'colors': [
            (-1.0, (180, 0, 0)),        # Dark red - significant decrease
            (-0.5, (255, 100, 100)),    # Light red - moderate decrease
            (-0.2, (255, 180, 180)),    # Pink - slight decrease
            (0.0, (255, 255, 255)),     # White - no change
            (0.2, (180, 255, 180)),     # Light green - slight increase
            (0.5, (100, 255, 100)),     # Green - moderate increase
            (1.0, (0, 180, 0)),         # Dark green - significant increase
        ],
        'nodata_color': (128, 128, 128),
    }
}


def interpolate_color(value: float, colormap: List[Tuple[float, Tuple[int, int, int]]]) -> Tuple[int, int, int]:
    """Interpolates a color from a colormap based on value."""
    if value <= colormap[0][0]:
        return colormap[0][1]
    if value >= colormap[-1][0]:
        return colormap[-1][1]
    
    # Find the two colors to interpolate between
    for i in range(len(colormap) - 1):
        if colormap[i][0] <= value <= colormap[i + 1][0]:
            v1, c1 = colormap[i]
            v2, c2 = colormap[i + 1]
            t = (value - v1) / (v2 - v1)
            r = int(c1[0] + t * (c2[0] - c1[0]))
            g = int(c1[1] + t * (c2[1] - c1[1]))
            b = int(c1[2] + t * (c2[2] - c1[2]))
            return (r, g, b)
    
    return colormap[-1][1]


def apply_colormap(
    data: np.ndarray,
    index_type: str,
    nodata_mask: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Applies a colormap to index data.
    
    Args:
        data: 2D numpy array of index values (typically -1 to 1)
        index_type: Type of index ('ndvi', 'ndwi', 'bsi', 'change')
        nodata_mask: Optional boolean mask where True indicates nodata
        
    Returns:
        3D numpy array (height, width, 3) of RGB values
    """
    colormap_config = COLORMAPS.get(index_type, COLORMAPS['ndvi'])
    colors = colormap_config['colors']
    nodata_color = colormap_config['nodata_color']
    
    # Create output RGB array
    height, width = data.shape
    rgb = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Vectorized colormap application
    # Clip values to valid range
    data_clipped = np.clip(data, -1.0, 1.0)
    
    # Apply colormap pixel by pixel (could be optimized with lookup table)
    for i in range(height):
        for j in range(width):
            if nodata_mask is not None and nodata_mask[i, j]:
                rgb[i, j] = nodata_color
            else:
                rgb[i, j] = interpolate_color(data_clipped[i, j], colors)
    
    return rgb


def apply_colormap_fast(
    data: np.ndarray,
    index_type: str,
    nodata_mask: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Fast vectorized colormap application using lookup table.
    
    Args:
        data: 2D numpy array of index values (typically -1 to 1)
        index_type: Type of index ('ndvi', 'ndwi', 'bsi', 'change')
        nodata_mask: Optional boolean mask where True indicates nodata
        
    Returns:
        3D numpy array (height, width, 3) of RGB values
    """
    colormap_config = COLORMAPS.get(index_type, COLORMAPS['ndvi'])
    colors = colormap_config['colors']
    nodata_color = colormap_config['nodata_color']
    
    # Create lookup table (256 entries for -1 to 1 range)
    lut_size = 256
    lut = np.zeros((lut_size, 3), dtype=np.uint8)
    for i in range(lut_size):
        value = -1.0 + (2.0 * i / (lut_size - 1))
        lut[i] = interpolate_color(value, colors)
    
    # Map data to lookup indices
    data_clipped = np.clip(data, -1.0, 1.0)
    indices = ((data_clipped + 1.0) * (lut_size - 1) / 2.0).astype(np.int32)
    indices = np.clip(indices, 0, lut_size - 1)
    
    # Apply lookup table
    rgb = lut[indices]
    
    # Apply nodata mask
    if nodata_mask is not None:
        rgb[nodata_mask] = nodata_color
    
    return rgb


def save_index_geotiff(
    data: np.ndarray,
    transform: Affine,
    crs: Any,
    output_path: str,
    nodata_value: float = -9999.0
) -> bool:
    """
    Saves an index array as a GeoTIFF.
    
    Args:
        data: 2D numpy array of index values
        transform: Rasterio affine transform
        crs: Coordinate reference system
        output_path: Output file path
        nodata_value: Value to use for nodata pixels
        
    Returns:
        True if successful
    """
    try:
        ensure_dirs()
        
        # Replace NaN with nodata
        data_clean = np.where(np.isnan(data), nodata_value, data)
        
        profile = {
            'driver': 'GTiff',
            'dtype': 'float32',
            'width': data.shape[1],
            'height': data.shape[0],
            'count': 1,
            'crs': crs,
            'transform': transform,
            'nodata': nodata_value,
            'compress': 'lzw'
        }
        
        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(data_clean.astype(np.float32), 1)
        
        return True
    except Exception as e:
        print(f"  ✗ Failed to save GeoTIFF: {e}")
        return False


def generate_index_preview(
    data: np.ndarray,
    index_type: str,
    output_name: str,
    nodata_mask: Optional[np.ndarray] = None
) -> Tuple[str, str]:
    """
    Generates a colormapped PNG preview of an index.
    
    Args:
        data: 2D numpy array of index values
        index_type: Type of index for colormap selection
        output_name: Name for output file
        nodata_mask: Optional mask for nodata pixels
        
    Returns:
        Tuple of (file_path, url_path)
    """
    ensure_dirs()
    
    output_path = PREVIEW_DIR / f"{output_name}.png"
    
    # Apply colormap
    rgb = apply_colormap_fast(data, index_type, nodata_mask)
    
    # Save as PNG
    img = Image.fromarray(rgb)
    img.save(output_path)
    
    url = f"/data/cache/{output_name}.png"
    return str(output_path), url


def generate_index(
    data: np.ndarray,
    transform: Affine,
    crs: Any,
    index_type: str,
    run_id: int,
    scene_label: str,  # 'baseline' or 'latest'
    save_geotiff: bool = True,
    generate_preview: bool = True
) -> IndexResult:
    """
    Generates a complete index output with GeoTIFF and preview.
    
    Args:
        data: 2D numpy array of index values
        transform: Rasterio affine transform
        crs: Coordinate reference system
        index_type: Type of index ('ndvi', 'ndwi', 'bsi')
        run_id: Analysis run ID
        scene_label: 'baseline' or 'latest'
        save_geotiff: Whether to save GeoTIFF
        generate_preview: Whether to generate preview PNG
        
    Returns:
        IndexResult with paths and metadata
    """
    ensure_dirs()
    
    try:
        output_name = f"run{run_id}_{scene_label}_{index_type}"
        
        # Calculate statistics
        valid_data = data[~np.isnan(data)]
        if len(valid_data) > 0:
            stats = {
                'min': float(np.min(valid_data)),
                'max': float(np.max(valid_data)),
                'mean': float(np.mean(valid_data)),
                'std': float(np.std(valid_data))
            }
        else:
            stats = {'min': 0, 'max': 0, 'mean': 0, 'std': 0}
        
        geotiff_path = None
        preview_path = None
        preview_url = None
        bounds = None
        
        # Save GeoTIFF
        if save_geotiff:
            geotiff_path = str(INDEX_DIR / f"{output_name}.tif")
            success = save_index_geotiff(data, transform, crs, geotiff_path)
            if success:
                bounds = get_raster_bounds_4326(geotiff_path)
            else:
                geotiff_path = None
        
        # Generate preview
        if generate_preview:
            nodata_mask = np.isnan(data) | (data == 0)
            preview_path, preview_url = generate_index_preview(
                data, index_type, output_name, nodata_mask
            )
        
        return IndexResult(
            success=True,
            index_type=index_type,
            geotiff_path=geotiff_path,
            preview_path=preview_path,
            preview_url=preview_url,
            bounds=bounds,
            stats=stats,
            message=f"Successfully generated {index_type.upper()} index"
        )
        
    except Exception as e:
        return IndexResult(
            success=False,
            index_type=index_type,
            geotiff_path=None,
            preview_path=None,
            preview_url=None,
            bounds=None,
            stats={},
            message=f"Failed to generate {index_type}: {str(e)}"
        )


def generate_change_preview(
    baseline_data: np.ndarray,
    latest_data: np.ndarray,
    transform: Affine,
    crs: Any,
    index_type: str,
    run_id: int
) -> IndexResult:
    """
    Generates a change detection preview between two time periods.
    
    Args:
        baseline_data: Baseline index array
        latest_data: Latest index array
        transform: Rasterio affine transform
        crs: Coordinate reference system
        index_type: Type of index ('ndvi', 'ndwi', 'bsi')
        run_id: Analysis run ID
        
    Returns:
        IndexResult for the change layer
    """
    ensure_dirs()
    
    try:
        # Calculate change
        change = latest_data - baseline_data
        
        output_name = f"run{run_id}_change_{index_type}"
        
        # Calculate statistics
        valid_change = change[~np.isnan(change)]
        if len(valid_change) > 0:
            stats = {
                'min': float(np.min(valid_change)),
                'max': float(np.max(valid_change)),
                'mean': float(np.mean(valid_change)),
                'std': float(np.std(valid_change)),
                'decrease_pixels': int(np.sum(valid_change < -0.1)),
                'increase_pixels': int(np.sum(valid_change > 0.1)),
            }
        else:
            stats = {'min': 0, 'max': 0, 'mean': 0, 'std': 0}
        
        # Save GeoTIFF
        geotiff_path = str(INDEX_DIR / f"{output_name}.tif")
        save_index_geotiff(change, transform, crs, geotiff_path)
        bounds = get_raster_bounds_4326(geotiff_path)
        
        # Generate preview with change colormap
        nodata_mask = np.isnan(change)
        preview_path, preview_url = generate_index_preview(
            change, 'change', output_name, nodata_mask
        )
        
        return IndexResult(
            success=True,
            index_type=f"{index_type}_change",
            geotiff_path=geotiff_path,
            preview_path=preview_path,
            preview_url=preview_url,
            bounds=bounds,
            stats=stats,
            message=f"Successfully generated {index_type.upper()} change layer"
        )
        
    except Exception as e:
        return IndexResult(
            success=False,
            index_type=f"{index_type}_change",
            geotiff_path=None,
            preview_path=None,
            preview_url=None,
            bounds=None,
            stats={},
            message=f"Failed to generate change layer: {str(e)}"
        )


def generate_all_indices(
    bands: Dict[str, np.ndarray],
    transform: Affine,
    crs: Any,
    run_id: int,
    scene_label: str
) -> Dict[str, IndexResult]:
    """
    Generates all indices (NDVI, NDWI, BSI) from band data.
    
    Args:
        bands: Dict with band arrays {'B02': ..., 'B03': ..., 'B04': ..., 'B08': ..., 'B11': ...}
        transform: Rasterio affine transform
        crs: Coordinate reference system
        run_id: Analysis run ID
        scene_label: 'baseline' or 'latest'
        
    Returns:
        Dict mapping index names to IndexResult
    """
    from backend.utils.spatial import calculate_ndvi, calculate_ndwi, calculate_bsi
    
    results = {}
    
    # Calculate NDVI
    if 'B04' in bands and 'B08' in bands:
        ndvi = calculate_ndvi(bands['B04'], bands['B08'])
        results['ndvi'] = generate_index(ndvi, transform, crs, 'ndvi', run_id, scene_label)
    
    # Calculate NDWI
    if 'B03' in bands and 'B08' in bands:
        ndwi = calculate_ndwi(bands['B03'], bands['B08'])
        results['ndwi'] = generate_index(ndwi, transform, crs, 'ndwi', run_id, scene_label)
    
    # Calculate BSI
    if all(b in bands for b in ['B02', 'B04', 'B08', 'B11']):
        bsi = calculate_bsi(bands['B04'], bands['B02'], bands['B08'], bands['B11'])
        results['bsi'] = generate_index(bsi, transform, crs, 'bsi', run_id, scene_label)
    
    return results
