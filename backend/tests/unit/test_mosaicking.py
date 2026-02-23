import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from backend.utils.mosaicking import create_mosaic, MOSAIC_DIR
from backend.utils.coverage_validator import find_optimal_scenes

def test_find_optimal_scenes_greedy(sample_boundary):
    """Test that the greedy algorithm selects minimum scenes for coverage."""
    # Scene 1: covers left half
    # Scene 2: covers right half
    # Scene 3: overlapping with both
    
    scenes = [
        {
            "id": "scene_left",
            "footprint": {"type": "Polygon", "coordinates": [[[-0.1, -0.1], [0.05, -0.1], [0.05, 0.2], [-0.1, 0.2], [-0.1, -0.1]]]},
            "cloud_cover": 10
        },
        {
            "id": "scene_right",
            "footprint": {"type": "Polygon", "coordinates": [[[0.05, -0.1], [0.2, -0.1], [0.2, 0.2], [0.05, 0.2], [0.05, -0.1]]]},
            "cloud_cover": 10
        },
        {
            "id": "scene_waste",
            "footprint": {"type": "Polygon", "coordinates": [[[0.0, 0.0], [0.1, 0.0], [0.1, 0.1], [0.0, 0.1], [0.0, 0.0]]]},
            "cloud_cover": 50
        }
    ]
    
    # Target boundary covers [0.0, 0.1] in both dims
    selected = find_optimal_scenes(scenes, sample_boundary, prefer_less_cloud=True)
    
    assert "scene_left" in selected
    assert "scene_right" in selected
    # "scene_waste" should not be selected if coverage is already met by better scenes
    assert "scene_waste" not in selected

def test_create_mosaic_multiple_files(mock_raster_file, sample_boundary, tmp_path):
    """Test creating a mosaic from multiple mock raster files."""
    p1 = mock_raster_file("tile1.tif")
    p2 = mock_raster_file("tile2.tif")
    
    # Mock MOSAIC_DIR to avoid writing to real data dir
    with patch("backend.utils.mosaicking.MOSAIC_DIR", tmp_path):
        result = create_mosaic([p1, p2], "test_mosaic", boundary_geojson=sample_boundary)
        
        assert result.success
        assert result.source_count == 2
        assert Path(result.output_path).exists()
        assert "clipped" in result.output_path

def test_create_mosaic_single_file(mock_raster_file, sample_boundary, tmp_path):
    """Test that creating a mosaic with one file just returns/clips that file."""
    p1 = mock_raster_file("single.tif")
    
    with patch("backend.utils.mosaicking.MOSAIC_DIR", tmp_path):
        result = create_mosaic([p1], "single_proc", boundary_geojson=sample_boundary)
        
        assert result.success
        assert result.source_count == 1
        assert "single_proc" in result.output_path
