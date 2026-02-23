import pytest
import requests
from unittest.mock import MagicMock, patch
from backend.utils.stac_downloader import (
    download_sentinel2_bands,
    get_scene_footprint,
    DATA_DIR
)

@pytest.fixture
def mock_stac_item():
    """Sample STAC item response."""
    return {
        "id": "S2A_MSIL2A_TEST",
        "geometry": {"type": "Polygon", "coordinates": [[[0,0], [1,0], [1,1], [0,0]]]},
        "assets": {
            "B04": {"href": "https://example.com/B04.tif"},
            "B08": {"href": "https://example.com/B08.tif"}
        }
    }

def test_get_scene_footprint(mock_requests, mock_stac_item):
    """Test fetching scene footprint with mocked API."""
    mock_get, _ = mock_requests
    mock_get.return_value.json.return_value = mock_stac_item
    mock_get.return_value.status_code = 200
    
    footprint = get_scene_footprint("S2A_MSIL2A_TEST")
    assert footprint == mock_stac_item["geometry"]
    assert mock_get.called

def test_download_sentinel2_bands_success(mock_requests, mock_stac_item, tmp_path):
    """Test successful band download with mocked signing and streaming."""
    mock_get, _ = mock_requests
    
    # Mock sequence of calls: 1. Fetch item, 2. Sign B04, 3. Download B04
    mock_item_resp = MagicMock()
    mock_item_resp.json.return_value = mock_stac_item
    mock_item_resp.status_code = 200
    
    mock_sign_resp = MagicMock()
    mock_sign_resp.json.return_value = {"href": "https://example.com/signed_B04.tif"}
    mock_sign_resp.status_code = 200
    
    mock_dl_resp = MagicMock()
    mock_dl_resp.iter_content.return_value = [b"data_chunk"]
    mock_dl_resp.headers = {"content-length": "10"}
    mock_dl_resp.status_code = 200
    
    mock_get.side_effect = [mock_item_resp, mock_sign_resp, mock_dl_resp]
    
    # Overwrite DATA_DIR for test to avoid writing to real data dir
    with patch("backend.utils.stac_downloader.DATA_DIR", tmp_path):
        paths = download_sentinel2_bands("S2A_MSIL2A_TEST", ["B04"])
        
        assert "B04" in paths
        assert (tmp_path / "S2A_MSIL2A_TEST_B04.tif").exists()

def test_download_sentinel2_bands_missing_asset(mock_requests, mock_stac_item):
    """Test error when requested band is missing from STAC item."""
    mock_get, _ = mock_requests
    mock_get.return_value.json.return_value = mock_stac_item
    mock_get.return_value.status_code = 200
    
    with pytest.raises(ValueError, match="Band B02 not found"):
        download_sentinel2_bands("S2A_MSIL2A_TEST", ["B02"])

def test_download_sentinel2_bands_network_failure(mock_requests):
    """Test cleanup or error handling on network failure."""
    mock_get, _ = mock_requests
    mock_get.side_effect = requests.exceptions.RequestException("Connection error")
    
    with pytest.raises(requests.exceptions.RequestException):
        download_sentinel2_bands("S2A_MSIL2A_TEST", ["B04"])
