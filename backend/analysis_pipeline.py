from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


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
    zones = [
        Zone(
            zone_type="vegetation_loss",
            area_ha=1.5,
            geometry={
                "type": "Polygon",
                "coordinates": [
                    [
                        [7.491, 9.137],
                        [7.493, 9.138],
                        [7.494, 9.136],
                        [7.492, 9.135],
                        [7.491, 9.137],
                    ]
                ],
            },
        ),
        Zone(
            zone_type="vegetation_gain",
            area_ha=0.8,
            geometry={
                "type": "Polygon",
                "coordinates": [
                    [
                        [7.496, 9.134],
                        [7.498, 9.135],
                        [7.497, 9.133],
                        [7.495, 9.132],
                        [7.496, 9.134],
                    ]
                ],
            },
        ),
        Zone(
            zone_type="alert",
            area_ha=0.5,
            geometry={
                "type": "Polygon",
                "coordinates": [
                    [
                        [7.489, 9.132],
                        [7.491, 9.133],
                        [7.490, 9.131],
                        [7.488, 9.130],
                        [7.489, 9.132],
                    ]
                ],
            },
        ),
    ]

    alerts = [
        Alert(
            alert_type="vegetation_loss",
            title="Vegetation loss near quarry lake",
            description="NDVI analysis shows decline in vegetation cover on the western ridge of Mpape quarry.",
            location="Mpape West Ridge",
            severity="high",
        ),
        Alert(
            alert_type="boundary_breach",
            title="Unauthorized access detected",
            description="Movement patterns suggest potential trespassing in the restricted lake sector.",
            location="Quarry Lake Restricted Area",
            severity="medium",
        ),
        Alert(
            alert_type="threshold_exceeded",
            title="Dust level advisory",
            description="Surface reflectance indicators suggest elevated dust levels in active stone crushing zones.",
            location="Crushing Sector A",
            severity="low",
        ),
    ]

    # Placeholder for a real NDVI pipeline.
    # If you later install raster dependencies and provide local file URIs, this function
    # can compute NDVI differencing and generate real zones.
    # For now we keep the app fully runnable by falling back to the demo zones.
    if baseline_scene is not None and latest_scene is not None:
        _ = baseline_scene
        _ = latest_scene

    _ = mine_area
    _ = baseline_date
    _ = latest_date

    return zones, alerts
