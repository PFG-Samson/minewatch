import pytest
import numpy as np
from backend.utils.coverage_validator import (
    validate_coverage,
    validate_multi_scene_coverage,
    get_raster_footprint,
    CoverageResult
)
from shapely.geometry import shape, mapping

def test_get_raster_footprint(mock_raster_file):
    """Test extracting footprint from a raster file."""
    path = mock_raster_file("test_footprint.tif")
    footprint = get_raster_footprint(path)
    
    assert footprint["type"] == "Polygon"
    assert "coordinates" in footprint

def test_validate_coverage_full(mock_raster_file):
    """Test full coverage scenario."""
    # Create a 1x1 degree raster at 0,0
    from rasterio.transform import from_origin
    transform = from_origin(0.0, 1.0, 0.1, 0.1)
    path = mock_raster_file("full_cov.tif", transform=transform)
    
    # Boundary within that range
    boundary = {
        "type": "Polygon",
        "coordinates": [[
            [0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8], [0.2, 0.2]
        ]]
    }
    
    result = validate_coverage(path, boundary, check_valid_data=False)
    assert result.is_valid
    assert result.coverage_percent == 100.0

def test_validate_coverage_partial(mock_raster_file):
    """Test partial coverage scenario."""
    from rasterio.transform import from_origin
    # Raster covers 0.0 to 1.0 lon/lat (10 pixels * 0.1)
    transform = from_origin(0.0, 1.0, 0.1, 0.1)
    path = mock_raster_file("partial_cov.tif", shape=(10, 10), transform=transform)
    
    # Boundary spans 0.5 to 1.5 lon
    boundary = {
        "type": "Polygon",
        "coordinates": [[
            [0.5, 0.0], [1.5, 0.0], [1.5, 1.0], [0.5, 1.0], [0.5, 0.0]
        ]]
    }
    
    result = validate_coverage(path, boundary, min_coverage_percent=40.0, check_valid_data=False)
    # Intersection check: (1.0-0.5) * (1.0-0.0) = 0.5
    # Total area: (1.5-0.5) * (1.0-0.0) = 1.0
    # Expected: 50%
    assert result.coverage_percent == 50.0
    assert result.is_valid

def test_validate_coverage_none(mock_raster_file):
    """Test no coverage scenario."""
    from rasterio.transform import from_origin
    transform = from_origin(10.0, 20.0, 0.1, 0.1)
    path = mock_raster_file("no_cov.tif", transform=transform)
    
    boundary = {
        "type": "Polygon",
        "coordinates": [[
            [0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]
        ]]
    }
    
    result = validate_coverage(path, boundary)
    assert not result.is_valid
    assert result.coverage_percent == 0.0

def test_validate_multi_scene_coverage(mock_raster_file):
    """Test coverage from multiple scenes."""
    from rasterio.transform import from_origin
    # Two scenes that together cover the boundary
    p1 = mock_raster_file("p1.tif", transform=from_origin(0.0, 1.0, 0.1, 0.1))
    p2 = mock_raster_file("p2.tif", transform=from_origin(1.0, 1.0, 0.1, 0.1))
    
    boundary = {
        "type": "Polygon",
        "coordinates": [[
            [0.5, 0.0], [1.5, 0.0], [1.5, 1.0], [0.5, 1.0], [0.5, 0.0]
        ]]
    }
    
    result, contributing = validate_multi_scene_coverage([p1, p2], boundary)
    assert result.is_valid
    assert result.coverage_percent == 100.0
    assert len(contributing) == 2
