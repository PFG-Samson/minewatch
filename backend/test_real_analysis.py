"""
Diagnostic test script for real NDVI analysis pipeline.
Run this to verify that real satellite imagery analysis is working.

Usage:
    python -m backend.test_real_analysis
"""
import json
import sqlite3
from pathlib import Path
from typing import Optional

from backend.analysis_pipeline import run_analysis, ImageryScene


def main():
    """Run diagnostic tests on the real analysis pipeline."""
    print("=" * 70)
    print("MineWatch Real Analysis Diagnostic Test")
    print("=" * 70)
    print()

    # Step 1: Check if imagery files exist
    print("1. Checking for downloaded imagery files...")
    imagery_dir = Path(__file__).parent / "data" / "imagery"
    if not imagery_dir.exists():
        print(f"   ❌ ERROR: Imagery directory not found: {imagery_dir}")
        return
    
    tif_files = list(imagery_dir.glob("*.tif"))
    if not tif_files:
        print(f"   ❌ ERROR: No .tif files found in {imagery_dir}")
        print("   → Run STAC ingestion job first to download imagery")
        return
    
    print(f"   ✅ Found {len(tif_files)} imagery files")
    
    # Group files by scene ID
    scenes = {}
    for tif_file in tif_files:
        # Extract scene ID (everything before the last underscore and band name)
        parts = tif_file.stem.rsplit('_', 1)
        if len(parts) == 2:
            scene_id, band = parts
            if scene_id not in scenes:
                scenes[scene_id] = []
            scenes[scene_id].append(band)
    
    print(f"   ✅ Found {len(scenes)} unique scenes")
    for scene_id, bands in scenes.items():
        print(f"      - {scene_id}: {', '.join(sorted(bands))}")
    print()

    # Step 2: Load mine boundary from database
    print("2. Loading mine boundary from database...")
    db_path = Path(__file__).parent / "minewatch.db"
    if not db_path.exists():
        print(f"   ❌ ERROR: Database not found: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    mine_row = conn.execute("SELECT * FROM mine_area WHERE id = 1").fetchone()
    if mine_row is None:
        print("   ❌ ERROR: No mine boundary configured")
        print("   → Go to Settings tab and save a mine boundary first")
        conn.close()
        return
    
    mine_area = {
        "name": mine_row["name"],
        "boundary": json.loads(mine_row["boundary_geojson"]),
        "buffer_km": float(mine_row["buffer_km"])
    }
    print(f"   ✅ Loaded mine area: {mine_area['name']}")
    print(f"      Buffer: {mine_area['buffer_km']} km")
    print()

    # Step 3: Load imagery scenes from database
    print("3. Loading imagery scenes from database...")
    scene_rows = conn.execute(
        """
        SELECT id, source, acquired_at, cloud_cover, uri 
        FROM imagery_scene 
        ORDER BY acquired_at DESC 
        LIMIT 2
        """
    ).fetchall()
    
    if len(scene_rows) < 2:
        print(f"   ❌ ERROR: Need at least 2 scenes for comparison, found {len(scene_rows)}")
        print("   → Run STAC ingestion to download more scenes")
        conn.close()
        return
    
    baseline_row = scene_rows[1]  # Older scene
    latest_row = scene_rows[0]    # Newer scene
    
    baseline_scene = ImageryScene(
        id=int(baseline_row["id"]),
        source=baseline_row["source"],
        acquired_at=baseline_row["acquired_at"],
        cloud_cover=float(baseline_row["cloud_cover"]) if baseline_row["cloud_cover"] else None,
        uri=baseline_row["uri"]
    )
    
    latest_scene = ImageryScene(
        id=int(latest_row["id"]),
        source=latest_row["source"],
        acquired_at=latest_row["acquired_at"],
        cloud_cover=float(latest_row["cloud_cover"]) if latest_row["cloud_cover"] else None,
        uri=latest_row["uri"]
    )
    
    print(f"   ✅ Baseline scene: {baseline_scene.uri}")
    print(f"      Acquired: {baseline_scene.acquired_at}")
    print(f"      Cloud cover: {baseline_scene.cloud_cover}%")
    print()
    print(f"   ✅ Latest scene: {latest_scene.uri}")
    print(f"      Acquired: {latest_scene.acquired_at}")
    print(f"      Cloud cover: {latest_scene.cloud_cover}%")
    print()
    
    conn.close()

    # Step 4: Verify required bands exist for both scenes
    print("4. Verifying required bands for analysis...")
    required_bands = ["B02", "B03", "B04", "B08", "B11"]
    
    for scene_label, scene in [("Baseline", baseline_scene), ("Latest", latest_scene)]:
        print(f"   Checking {scene_label} ({scene.uri}):")
        missing_bands = []
        for band in required_bands:
            file_path = imagery_dir / f"{scene.uri}_{band}.tif"
            if file_path.exists():
                size_mb = file_path.stat().st_size / (1024 * 1024)
                print(f"      ✅ {band}: {size_mb:.1f} MB")
            else:
                print(f"      ❌ {band}: NOT FOUND")
                missing_bands.append(band)
        
        if missing_bands:
            print(f"   ❌ ERROR: Missing bands for {scene_label}: {', '.join(missing_bands)}")
            print("   → Re-run STAC ingestion or check download logs")
            return
    print()

    # Step 5: Run the actual analysis
    print("5. Running real NDVI analysis pipeline...")
    print("   This may take 2-5 minutes depending on scene size...")
    print()
    
    try:
        zones, alerts = run_analysis(
            mine_area=mine_area,
            baseline_date=baseline_scene.acquired_at,
            latest_date=latest_scene.acquired_at,
            baseline_scene=baseline_scene,
            latest_scene=latest_scene
        )
        
        print("=" * 70)
        print("ANALYSIS COMPLETE")
        print("=" * 70)
        print()
        print(f"Generated {len(zones)} zones:")
        
        if zones:
            zone_summary = {}
            for zone in zones:
                zone_type = zone.zone_type
                if zone_type not in zone_summary:
                    zone_summary[zone_type] = {"count": 0, "total_area": 0.0}
                zone_summary[zone_type]["count"] += 1
                zone_summary[zone_type]["total_area"] += zone.area_ha
            
            for zone_type, stats in sorted(zone_summary.items()):
                print(f"   - {zone_type.replace('_', ' ').title()}: {stats['count']} zones, {stats['total_area']:.2f} ha total")
        else:
            print("   (No zones detected - this may indicate no significant change)")
        
        print()
        print(f"Generated {len(alerts)} alerts:")
        if alerts:
            for i, alert in enumerate(alerts[:10], 1):  # Show first 10
                print(f"   {i}. [{alert.severity.upper()}] {alert.title}")
                print(f"      {alert.description}")
        else:
            print("   (No alerts generated)")
        
        print()
        print("=" * 70)
        print("✅ SUCCESS: Real analysis pipeline is working!")
        print("=" * 70)
        
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ ANALYSIS FAILED")
        print("=" * 70)
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print()
        print("Stack trace:")
        import traceback
        traceback.print_exc()
        print()
        print("This indicates that the real analysis pipeline has an issue.")
        print("Check the error message above for clues.")


if __name__ == "__main__":
    main()
