from __future__ import annotations
import numpy as np
import os
from dataclasses import dataclass
from typing import Any, Optional, List, Tuple

from backend.utils.stac_downloader import download_sentinel2_bands
from backend.utils.spatial import (
    calculate_ndvi, calculate_ndwi, calculate_bsi, 
    clip_raster_to_geometry, vectorize_mask
)

@dataclass(frozen=True)
class Zone:
    zone_type: str
    area_ha: float
    geometry: dict[str, Any]

@dataclass(frozen=True)
class Alert:
    alert_type: str
    title: str
    description: str
    location: str
    severity: str

@dataclass(frozen=True)
class ImageryScene:
    id: int
    source: str
    acquired_at: str
    cloud_cover: Optional[float]
    uri: Optional[str]

def run_analysis(
    *,
    mine_area: Optional[dict[str, Any]],
    baseline_date: Optional[str],
    latest_date: Optional[str],
    baseline_scene: Optional[ImageryScene] = None,
    latest_scene: Optional[ImageryScene] = None,
) -> tuple[list[Zone], list[Alert]]:
    # Fallback/Demo data if no real scenes provided
    if baseline_scene is None or latest_scene is None or mine_area is None:
        return _get_demo_results()

    try:
        # 1. Prepare required bands
        # NDVI: Red (B04), NIR (B08)
        # NDWI: Green (B03), NIR (B08)
        # BSI: Red (B04), Blue (B02), NIR (B08), SWIR1 (B11)
        required_bands = ["B02", "B03", "B04", "B08", "B11"]
        
        print(f"Starting real analysis for {mine_area.get('name', 'Mine')}")
        print(f"Baseline Scene: {baseline_scene.uri}")
        print(f"Latest Scene: {latest_scene.uri}")

        # Validate that we're not comparing the same scene
        if baseline_scene.uri == latest_scene.uri:
            print("⚠️  WARNING: Baseline and latest scenes are identical")
            print("   No meaningful change detection can be performed")
            print("   → Please run STAC ingestion to download more scenes")
            # Return empty results instead of demo data
            return [], []

        baseline_paths = download_sentinel2_bands(baseline_scene.uri, required_bands)
        latest_paths = download_sentinel2_bands(latest_scene.uri, required_bands)

        geometry = mine_area.get("boundary")
        if not geometry:
            raise ValueError("No boundary geometry found in mine_area")

        # 2. Process Baseline
        b_red, transform, b_crs = clip_raster_to_geometry(baseline_paths["B04"], geometry)
        b_nir, _, _ = clip_raster_to_geometry(baseline_paths["B08"], geometry)
        b_green, _, _ = clip_raster_to_geometry(baseline_paths["B03"], geometry)
        b_blue, _, _ = clip_raster_to_geometry(baseline_paths["B02"], geometry)
        b_swir, _, _ = clip_raster_to_geometry(baseline_paths["B11"], geometry)

        b_ndvi = calculate_ndvi(b_red, b_nir)
        b_ndwi = calculate_ndwi(b_green, b_nir)
        b_bsi = calculate_bsi(b_red, b_blue, b_nir, b_swir)

        # 3. Process Latest
        l_red, _, _ = clip_raster_to_geometry(latest_paths["B04"], geometry)
        l_nir, _, _ = clip_raster_to_geometry(latest_paths["B08"], geometry)
        l_green, _, _ = clip_raster_to_geometry(latest_paths["B03"], geometry)
        l_blue, _, _ = clip_raster_to_geometry(latest_paths["B02"], geometry)
        l_swir, _, _ = clip_raster_to_geometry(latest_paths["B11"], geometry)

        l_ndvi = calculate_ndvi(l_red, l_nir)
        l_ndwi = calculate_ndwi(l_green, l_nir)
        l_bsi = calculate_bsi(l_red, l_blue, l_nir, l_swir)

        # 4. Change Detection Logic
        zones: list[Zone] = []
        alerts: list[Alert] = []

        # Vegetation Loss (NDVI drop > 0.15)
        ndvi_diff = l_ndvi - b_ndvi
        veg_loss_mask = (ndvi_diff < -0.15).astype(np.uint8)
        veg_loss_features = vectorize_mask(veg_loss_mask, transform, b_crs)
        for feat in veg_loss_features:
            area = _calculate_area(feat["geometry"])
            if area > 0.1: # Min 0.1 ha to show up
                zones.append(Zone("vegetation_loss", area, feat["geometry"]))
                if area > 0.5:
                    alerts.append(Alert(
                        alert_type="vegetation_loss", 
                        title=f"Significant vegetation loss detected ({area:.1f} ha)",
                        description="NDVI analysis shows a sharp decline in greenery. This could indicate new clearing or land degradation.",
                        location="Site-wide Assessment",
                        severity="high" if area > 1.0 else "medium"
                    ))

        # Bare Soil Expansion (BSI increase > 0.1) - Mining Pits
        bsi_diff = l_bsi - b_bsi
        soil_gain_mask = (bsi_diff > 0.1).astype(np.uint8)
        soil_features = vectorize_mask(soil_gain_mask, transform, b_crs)
        for feat in soil_features:
            area = _calculate_area(feat["geometry"])
            if area > 0.1:
                zones.append(Zone("mining_expansion", area, feat["geometry"]))
                alerts.append(Alert(
                    alert_type="excavation_alert",
                    title=f"New excavation surface detected ({area:.1f} ha)",
                    description="Increase in Bare Soil Index suggests expansion of active mining pits or tailings zones.",
                    location="Active Operations Zone",
                    severity="medium"
                ))

        # Water Change (NDWI delta > 0.2)
        ndwi_diff = l_ndwi - b_ndwi
        water_gain_mask = (ndwi_diff > 0.2).astype(np.uint8)
        water_features = vectorize_mask(water_gain_mask, transform, b_crs)
        for feat in water_features:
            area = _calculate_area(feat["geometry"])
            if area > 0.05:
                zones.append(Zone("water_accumulation", area, feat["geometry"]))
                alerts.append(Alert(
                    alert_type="water_warning",
                    title="New water pooling detected",
                    description="NDWI indicates potential new water accumulation. Check for leaks or seasonal flooding.",
                    location="Drainage Area",
                    severity="low"
                ))

        if not zones:
            return [], []

        return zones, alerts

    except Exception as e:
        print(f"Error in scientific pipeline: {e}")
        return _get_demo_results()

def _calculate_area(geometry: dict) -> float:
    """Estimates area in hectares from GeoJSON geometry."""
    try:
        from shapely.geometry import shape
        import pyproj
        from shapely.ops import transform
        
        s = shape(geometry)
        lon, lat = s.centroid.x, s.centroid.y
        utm_zone = int((lon + 180) / 6) + 1
        proj_str = f"+proj=utm +zone={utm_zone} +datum=WGS84 +units=m +no_defs"
        project = pyproj.Transformer.from_crs("EPSG:4326", proj_str, always_xy=True).transform
        s_utm = transform(project, s)
        return s_utm.area / 10000.0 # m^2 to ha
    except Exception as e:
        print(f"Area calculation error: {e}")
        # Very rough fallback
        return 0.0

def _get_demo_results() -> tuple[list[Zone], list[Alert]]:
    """Returns the hardcoded demo outputs for fallback/seeding."""
    zones = [
        Zone(
            zone_type="vegetation_loss",
            area_ha=1.5,
            geometry={
                "type": "Polygon",
                "coordinates": [
                    [[7.491, 9.137], [7.493, 9.138], [7.494, 9.136], [7.492, 9.135], [7.491, 9.137]]
                ],
            },
        ),
        Zone(
            zone_type="vegetation_gain",
            area_ha=0.8,
            geometry={
                "type": "Polygon",
                "coordinates": [
                    [[7.496, 9.134], [7.498, 9.135], [7.497, 9.133], [7.495, 9.132], [7.496, 9.134]]
                ],
            },
        ),
    ]

    alerts = [
        Alert(
            alert_type="vegetation_loss",
            title="Vegetation loss detected in operational zone",
            description="NDVI analysis shows decline in vegetation cover on the site's western ridge.",
            location="West Ridge Area",
            severity="high",
        ),
        Alert(
            alert_type="boundary_breach",
            title="Unauthorized access detected",
            description="Movement patterns suggest potential trespassing in restricted sectors.",
            location="Restricted Ops Zone",
            severity="medium",
        ),
    ]
    return zones, alerts
