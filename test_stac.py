
import sys
import os
import json
from backend.main import _bbox_from_geojson, _stac_search

def test_stac():
    boundary = {
        "type": "Polygon",
        "coordinates": [
            [[7.490, 9.138], [7.495, 9.140], [7.500, 9.135], [7.498, 9.130], [7.492, 9.128], [7.488, 9.132], [7.490, 9.138]]
        ]
    }
    
    bbox = _bbox_from_geojson(boundary)
    print(f"BBOX: {bbox}")
    
    if not bbox:
        print("Failed to derive bbox")
        return

    try:
        results = _stac_search(
            bbox=bbox,
            collection="sentinel-2-l2a",
            max_items=10,
            cloud_cover_lte=20.0
        )
        print(f"Results Count: {len(results.get('features', []))}")
        if results.get('features'):
            print(f"First result ID: {results['features'][0]['id']}")
    except Exception as e:
        print(f"Search failed: {e}")

if __name__ == "__main__":
    test_stac()
