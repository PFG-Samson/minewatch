import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.features import shapes
from rasterio.warp import transform_geom, transform_bounds
from shapely.geometry import shape, mapping
from typing import Any, Tuple, List

def calculate_ndvi(red_band: np.ndarray, nir_band: np.ndarray) -> np.ndarray:
    """Calculates Normalized Difference Vegetation Index (NDVI)."""
    # Use numeric types to avoid overflow and divide-by-zero warnings
    red = red_band.astype(float)
    nir = nir_band.astype(float)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        ndvi = (nir - red) / (nir + red)
    
    # Clean up NaNs and Infinities
    ndvi = np.nan_to_num(ndvi, nan=0.0, posinf=0.0, neginf=0.0)
    return ndvi

def calculate_ndwi(green_band: np.ndarray, nir_band: np.ndarray) -> np.ndarray:
    """Calculates Normalized Difference Water Index (NDWI) for water detection."""
    green = green_band.astype(float)
    nir = nir_band.astype(float)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        ndwi = (green - nir) / (green + nir)
    
    ndwi = np.nan_to_num(ndwi, nan=0.0, posinf=0.0, neginf=0.0)
    return ndwi

def calculate_bsi(red: np.ndarray, blue: np.ndarray, nir: np.ndarray, swir: np.ndarray) -> np.ndarray:
    """Calculates Bare Soil Index (BSI)."""
    # Formula: ((SWIR + Red) - (NIR + Blue)) / ((SWIR + Red) + (NIR + Blue))
    r = red.astype(float)
    b = blue.astype(float)
    n = nir.astype(float)
    s = swir.astype(float)
    
    numerator = (s + r) - (n + b)
    denominator = (s + r) + (n + b)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        bsi = numerator / denominator
        
    bsi = np.nan_to_num(bsi, nan=0.0, posinf=0.0, neginf=0.0)
    return bsi

def _extract_geometry(geojson_input: dict) -> dict:
    """
    Extracts a single geometry from various GeoJSON formats.
    
    Handles:
    - Geometry objects (Polygon, MultiPolygon, etc.)
    - Feature objects
    - FeatureCollection objects (uses first feature)
    
    Returns:
        A geometry dict suitable for rasterio operations
    
    Raises:
        ValueError: If geometry cannot be extracted
    """
    if not isinstance(geojson_input, dict):
        raise ValueError(f"Expected dict, got {type(geojson_input)}")
    
    geom_type = geojson_input.get("type")
    
    # Already a geometry object
    if geom_type in ["Point", "LineString", "Polygon", "MultiPoint", "MultiLineString", "MultiPolygon", "GeometryCollection"]:
        return geojson_input
    
    # Feature object - extract geometry
    if geom_type == "Feature":
        geometry = geojson_input.get("geometry")
        if not geometry:
            raise ValueError("Feature has no geometry property")
        return geometry
    
    # FeatureCollection - use first feature
    if geom_type == "FeatureCollection":
        features = geojson_input.get("features", [])
        if not features:
            raise ValueError("FeatureCollection has no features")
        first_feature = features[0]
        geometry = first_feature.get("geometry")
        if not geometry:
            raise ValueError("First feature has no geometry")
        return geometry
    
    raise ValueError(f"Unsupported GeoJSON type: {geom_type}")


def clip_raster_to_geometry(raster_path: str, geojson_geometry: dict) -> Tuple[np.ndarray, Any, Any]:
    """Clips a raster file to the provided GeoJSON geometry, handling CRS transformation."""
    # Extract geometry from various GeoJSON formats
    geometry = _extract_geometry(geojson_geometry)
    
    with rasterio.open(raster_path) as src:
        # Warp GeoJSON geometry to the raster's native CRS (usually UTM)
        warped_geom = transform_geom('EPSG:4326', src.crs, geometry)
        geoms = [shape(warped_geom)]
        out_image, out_transform = mask(src, geoms, crop=True)
        return out_image[0], out_transform, src.crs

def get_raster_bounds_4326(raster_path: str) -> List[float]:
    """Returns [min_lat, min_lon, max_lat, max_lon] in WGS84 (EPSG:4326)."""
    with rasterio.open(raster_path) as src:
        # transform_bounds returns (left, bottom, right, top) -> (min_lon, min_lat, max_lon, max_lat)
        bounds = transform_bounds(src.crs, 'EPSG:4326', *src.bounds)
        return [bounds[1], bounds[0], bounds[3], bounds[2]]

def vectorize_mask(mask_array: np.ndarray, transform: Any, src_crs: Any) -> List[dict]:
    """Converts a binary mask (numpy array) into a list of GeoJSON features in 4326."""
    results = []
    for s, v in shapes(mask_array.astype(np.int16), mask=mask_array > 0, transform=transform):
        # Warp the shape back to WGS84
        warped_s = transform_geom(src_crs, 'EPSG:4326', s)
        results.append({
            "properties": {"raster_value": v},
            "geometry": warped_s
        })
    return results
