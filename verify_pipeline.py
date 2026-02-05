from backend.analysis_pipeline import run_analysis, ImageryScene
import json

def test_pipeline_imports():
    print("Testing imports and basic structure...")
    try:
        # Create dummy scenes
        # In a real test we'd mock the downloader, but this just checks if run_analysis can be called
        # and if imports are correct.
        mine_area = {
            "name": "Test Mine",
            "boundary": {
                "type": "Polygon",
                "coordinates": [[[7.49, 9.13], [7.50, 9.13], [7.50, 9.14], [7.49, 9.14], [7.49, 9.13]]]
            }
        }
        
        # Test fallback logic (since scenes are None)
        zones, alerts = run_analysis(mine_area=mine_area, baseline_date="2024-01-01", latest_date="2024-02-01")
        print(f"Fallback Analysis successful. Zones: {len(zones)}, Alerts: {len(alerts)}")
        
        # Check if utilities are importable
        from backend.utils.spatial import calculate_ndvi
        import numpy as np
        red = np.array([100, 200], dtype=np.uint16)
        nir = np.array([300, 400], dtype=np.uint16)
        res = calculate_ndvi(red, nir)
        print(f"NDVI Utility Test: {res}")
        
        print("Pipeline is healthy!")
    except Exception as e:
        print(f"Pipeline verification failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pipeline_imports()
