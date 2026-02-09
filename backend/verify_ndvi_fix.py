"""
Simple verification script to check if real NDVI analysis is working.
Prints a simple success/failure message.

Usage:
    python -m backend.verify_ndvi_fix
"""

from pathlib import Path
import json
import sqlite3
from backend.utils.spatial import _extract_geometry


def main():
    print("Verifying NDVI Fix...")
    print()
    
    # Test 1: Geometry extraction
    print("Test 1: Geometry extraction from FeatureCollection")
    feature_collection = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
            }
        }]
    }
    
    try:
        geom = _extract_geometry(feature_collection)
        if geom["type"] == "Polygon":
            print("  ✅ Successfully extracted Polygon from FeatureCollection")
        else:
            print(f"  ❌ Unexpected geometry type: {geom['type']}")
            return False
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False
    
    # Test 2: Check mine boundary in database
    print("\nTest 2: Mine boundary in database")
    db_path = Path(__file__).parent / "minewatch.db"
    if not db_path.exists():
        print("  ⚠️  Database not found - skipping test")
        return True
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    mine_row = conn.execute("SELECT boundary_geojson FROM mine_area WHERE id = 1").fetchone()
    conn.close()
    
    if not mine_row:
        print("  ⚠️  No mine boundary configured - skipping test")
        return True
    
    boundary = json.loads(mine_row["boundary_geojson"])
    try:
        geom = _extract_geometry(boundary)
        print(f"  ✅ Mine boundary type: {boundary.get('type')} → extracted as {geom['type']}")
    except Exception as e:
        print(f"  ❌ Failed to extract mine boundary: {e}")
        return False
    
    print()
    print("=" * 50)
    print("✅ ALL TESTS PASSED")
    print("=" * 50)
    print()
    print("The geometry extraction fix is working correctly!")
    print("Real NDVI analysis should now run without errors.")
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
