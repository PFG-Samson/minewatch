import numpy as np
import pytest
from backend.utils.spatial import (
    calculate_ndvi,
    calculate_ndwi,
    calculate_bsi,
    clip_raster_to_geometry,
    _extract_geometry
)

def test_ndvi_calculation():
    """Test NDVI formula and output range."""
    red = np.array([[100, 200], [300, 400]], dtype=np.uint16)
    nir = np.array([[500, 600], [700, 800]], dtype=np.uint16)
    
    ndvi = calculate_ndvi(red, nir)
    
    # Formula: (NIR - Red) / (NIR + Red)
    # (500-100)/(500+100) = 400/600 = 0.666...
    assert np.allclose(ndvi[0, 0], 0.66666667)
    assert ndvi.min() >= -1.0
    assert ndvi.max() <= 1.0

def test_ndvi_division_by_zero():
    """Test NDVI handling of zero NIR + Red."""
    red = np.array([[0]], dtype=np.uint16)
    nir = np.array([[0]], dtype=np.uint16)
    
    ndvi = calculate_ndvi(red, nir)
    assert ndvi[0, 0] == 0.0
    assert not np.isnan(ndvi).any()

def test_ndwi_calculation():
    """Test NDWI formula."""
    green = np.array([[200]], dtype=np.uint16)
    nir = np.array([[100]], dtype=np.uint16)
    
    ndwi = calculate_ndwi(green, nir)
    # (200-100)/(200+100) = 100/300 = 0.333...
    assert np.allclose(ndwi[0, 0], 0.33333333)

def test_bsi_calculation():
    """Test BSI formula."""
    red = np.array([[100]], dtype=np.uint16)
    blue = np.array([[50]], dtype=np.uint16)
    nir = np.array([[150]], dtype=np.uint16)
    swir = np.array([[200]], dtype=np.uint16)
    
    bsi = calculate_bsi(red, blue, nir, swir)
    # Formula: ((SWIR + Red) - (NIR + Blue)) / ((SWIR + Red) + (NIR + Blue))
    # ((200 + 100) - (150 + 50)) / ((200 + 100) + (150 + 50))
    # (300 - 200) / (300 + 200) = 100 / 500 = 0.2
    assert np.allclose(bsi[0, 0], 0.2)

def test_extract_geometry_formats():
    """Test geometry extraction from various GeoJSON formats."""
    poly = {"type": "Polygon", "coordinates": [[[0,0], [1,0], [1,1], [0,0]]]}
    
    # Direct geometry
    assert _extract_geometry(poly) == poly
    
    # Feature
    feature = {"type": "Feature", "geometry": poly, "properties": {}}
    assert _extract_geometry(feature) == poly
    
    # FeatureCollection
    fc = {"type": "FeatureCollection", "features": [feature]}
    assert _extract_geometry(fc) == poly
    
    # Invalid
    with pytest.raises(ValueError):
        _extract_geometry({"type": "Invalid"})

def test_clip_raster_mocked(mock_raster_file, sample_boundary):
    """Test clipping function with a mocked raster file."""
    raster_path = mock_raster_file("test_clip.tif")
    
    # This will involve rasterio.mask, we verify it returns expected shapes
    out_band, out_transform, crs = clip_raster_to_geometry(raster_path, sample_boundary)
    
    assert isinstance(out_band, np.ndarray)
    assert out_band.shape == (1, 1) # Depends on transform, but with our 0.1 deg step it should be small
    assert crs == "EPSG:4326"
