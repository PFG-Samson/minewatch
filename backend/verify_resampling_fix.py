import numpy as np
import os
from backend.utils.spatial import clip_raster_to_geometry

def verify_fix():
    print("🚀 Verifying Spatial Resampling Fix...")
    
    # Use existing data from the cache or download folder if available
    # For a quick test, we can use any .jp2 or .tif file
    data_dir = "backend/data"
    search_ext = (".jp2", ".tif")
    
    files = []
    for root, _, filenames in os.walk(data_dir):
        for f in filenames:
            if f.endswith(search_ext):
                files.append(os.path.join(root, f))
    
    if len(files) < 2:
        print("❌ Not enough data files for verification. Please run an analysis in the app first.")
        return

    # Mock geometry (overlapping T33PUP area)
    mock_geometry = {
        "type": "Polygon",
        "coordinates": [[
            [13.8, -14.4],
            [13.9, -14.4],
            [13.9, -14.3],
            [13.8, -14.3],
            [13.8, -14.4]
        ]]
    }

    try:
        # 1. Get master grid from first file (simulating B04 10m)
        master_band, transform, crs = clip_raster_to_geometry(files[0], mock_geometry)
        target_shape = master_band.shape
        print(f"✅ Master Grid Shape: {target_shape}")

        # 2. Force second file to match master grid (simulating B11 20m upsampling)
        resampled_band, _, _ = clip_raster_to_geometry(files[1], mock_geometry, target_shape, transform)
        print(f"✅ Resampled Band Shape: {resampled_band.shape}")

        if resampled_band.shape == target_shape:
            print("✨ SUCCESS: Shapes match perfectly!")
        else:
            print(f"❌ FAILURE: Shape mismatch! {resampled_band.shape} != {target_shape}")

    except Exception as e:
        print(f"❌ Error during verification: {e}")

if __name__ == "__main__":
    verify_fix()
