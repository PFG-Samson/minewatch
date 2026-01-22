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
            area_ha=12.5,
            geometry={
                "type": "Polygon",
                "coordinates": [
                    [
                        [119.77, -23.545],
                        [119.78, -23.54],
                        [119.79, -23.55],
                        [119.775, -23.555],
                        [119.77, -23.545],
                    ]
                ],
            },
        ),
        Zone(
            zone_type="vegetation_gain",
            area_ha=8.3,
            geometry={
                "type": "Polygon",
                "coordinates": [
                    [
                        [119.80, -23.57],
                        [119.815, -23.565],
                        [119.82, -23.575],
                        [119.805, -23.58],
                        [119.80, -23.57],
                    ]
                ],
            },
        ),
        Zone(
            zone_type="alert",
            area_ha=3.2,
            geometry={
                "type": "Polygon",
                "coordinates": [
                    [
                        [119.76, -23.59],
                        [119.77, -23.585],
                        [119.775, -23.595],
                        [119.765, -23.60],
                        [119.76, -23.59],
                    ]
                ],
            },
        ),
    ]

    alerts = [
        Alert(
            alert_type="vegetation_loss",
            title="Significant vegetation loss detected",
            description="NDVI analysis shows 12.5 hectares of vegetation decline in the northwest sector.",
            location="Sector NW-3",
            severity="high",
        ),
        Alert(
            alert_type="boundary_breach",
            title="Activity detected outside boundary",
            description="Movement patterns suggest potential unauthorized expansion near buffer zone.",
            location="Buffer Zone East",
            severity="medium",
        ),
        Alert(
            alert_type="threshold_exceeded",
            title="Bare soil threshold exceeded",
            description="Current exposed soil area exceeds permitted levels by 8%.",
            location="Pit Area B",
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
