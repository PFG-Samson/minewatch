from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from backend.config import TEMPORAL_GROUPING, SCENE_CONFIG
from backend.utils.coverage_validator import extract_boundary_geometry
from shapely.geometry import shape
from shapely.ops import unary_union
import json


@dataclass(frozen=True)
class CoverageSet:
    epoch_time: str
    scene_ids: List[int]
    scene_uris: List[str]
    coverage_percent: float


def _parse_iso_datetime(dt_str: str) -> datetime:
    for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
        try:
            return datetime.strptime(dt_str.replace("+00:00", "").replace("Z", ""), fmt)
        except ValueError:
            continue
    raise ValueError(f"Could not parse datetime: {dt_str}")


def build_coverage_sets(
    db_conn,
    boundary_geojson: Dict[str, Any],
    max_cloud_cover: Optional[float] = None,
) -> List[CoverageSet]:
    """
    Groups scenes into acquisition epochs and computes combined AOI coverage.
    Returns valid coverage sets sorted in reverse chronological order (newest first).
    """
    if max_cloud_cover is None:
        max_cloud_cover = SCENE_CONFIG["MAX_CLOUD_COVER"]

    rows = db_conn.execute(
        """
        SELECT id, uri, acquired_at, cloud_cover, footprint_geojson
        FROM imagery_scene
        WHERE footprint_geojson IS NOT NULL
        ORDER BY acquired_at DESC
        """
    ).fetchall()

    if not rows:
        return []

    boundary_geom = extract_boundary_geometry(boundary_geojson)
    tolerance_min = float(TEMPORAL_GROUPING["EPOCH_TOLERANCE_MINUTES"])
    min_epoch_cov = float(TEMPORAL_GROUPING["MIN_EPOCH_COVERAGE_PERCENT"])

    # Build epochs by iterating chronologically (newest first).
    epochs: List[List[Dict[str, Any]]] = []
    current_epoch: List[Dict[str, Any]] = []
    current_epoch_time: Optional[datetime] = None

    for row in rows:
        r = {k: row[k] for k in row.keys()}
        # Filter by cloud cover
        cc = r.get("cloud_cover")
        if cc is not None and cc > max_cloud_cover:
            continue
        # Skip scenes without URI or footprint
        if not r.get("uri") or not r.get("footprint_geojson"):
            continue

        dt = _parse_iso_datetime(str(r["acquired_at"]))
        if current_epoch_time is None:
            current_epoch_time = dt
            current_epoch = [r]
            continue

        diff_min = abs((current_epoch_time - dt).total_seconds()) / 60.0
        if diff_min <= tolerance_min:
            current_epoch.append(r)
        else:
            if current_epoch:
                epochs.append(current_epoch)
            current_epoch_time = dt
            current_epoch = [r]

    if current_epoch:
        epochs.append(current_epoch)

    # Compute coverage for each epoch; keep only valid ones
    coverage_sets: List[CoverageSet] = []
    for ep in epochs:
        footprints = []
        scene_ids: List[int] = []
        scene_uris: List[str] = []
        epoch_time_str = str(ep[0]["acquired_at"])

        for r in ep:
            try:
                fp = json.loads(r["footprint_geojson"])
                footprints.append(fp)
                scene_ids.append(int(r["id"]))
                scene_uris.append(str(r["uri"]))
            except Exception:
                continue

        if not footprints:
            continue

        try:
            combined = unary_union([extract_boundary_geometry(fp) for fp in footprints])
            if not boundary_geom.intersects(combined):
                continue
            intersection = boundary_geom.intersection(combined)
            coverage = (intersection.area / boundary_geom.area) * 100.0
        except Exception:
            continue

        if coverage >= min_epoch_cov:
            coverage_sets.append(
                CoverageSet(
                    epoch_time=epoch_time_str,
                    scene_ids=scene_ids,
                    scene_uris=scene_uris,
                    coverage_percent=coverage,
                )
            )

    # Already in newest-first due to ORDER BY acquired_at DESC grouping
    return coverage_sets


def select_latest_two_sets(coverage_sets: List[CoverageSet]) -> Tuple[CoverageSet, CoverageSet]:
    """
    Selects latest and baseline coverage sets.
    Returns (latest_set, baseline_set).
    Raises ValueError if fewer than 2 valid sets.
    """
    if len(coverage_sets) < 2:
        raise ValueError("Insufficient complete temporal coverage sets (need at least 2)")
    latest = coverage_sets[0]
    baseline = coverage_sets[1]
    return latest, baseline


def build_coverage_sets_from_candidates(
    boundary_geojson: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    max_cloud_cover: Optional[float] = None,
) -> List[CoverageSet]:
    """
    Variant that builds coverage sets from provided candidate scenes (no DB access).
    Each candidate should provide: id, uri, acquired_at, cloud_cover, footprint_geojson (optional).
    If footprint_geojson is missing, attempts to fetch footprint via STAC API.
    """
    if max_cloud_cover is None:
        max_cloud_cover = SCENE_CONFIG["MAX_CLOUD_COVER"]

    boundary_geom = extract_boundary_geometry(boundary_geojson)
    tolerance_min = float(TEMPORAL_GROUPING["EPOCH_TOLERANCE_MINUTES"])
    min_epoch_cov = float(TEMPORAL_GROUPING["MIN_EPOCH_COVERAGE_PERCENT"])

    # Normalize candidate records
    recs: List[Dict[str, Any]] = []
    for c in candidates:
        cc = c.get("cloud_cover")
        if cc is not None and float(cc) > max_cloud_cover:
            continue
        uri = c.get("uri")
        if not uri:
            continue
        acquired_at = c.get("acquired_at")
        if not acquired_at:
            continue
        fp = c.get("footprint_geojson")
        if fp is None:
            try:
                from backend.utils.stac_downloader import get_scene_footprint
                fp = get_scene_footprint(str(uri))
            except Exception:
                fp = None
        if fp is None:
            continue
        recs.append({
            "id": c.get("id"),
            "uri": str(uri),
            "acquired_at": str(acquired_at),
            "footprint_geojson": json.dumps(fp) if isinstance(fp, dict) else fp
        })

    if not recs:
        return []

    # Sort newest first
    recs.sort(key=lambda r: _parse_iso_datetime(str(r["acquired_at"])), reverse=True)

    epochs: List[List[Dict[str, Any]]] = []
    current_epoch: List[Dict[str, Any]] = []
    current_epoch_time: Optional[datetime] = None

    for r in recs:
        dt = _parse_iso_datetime(str(r["acquired_at"]))
        if current_epoch_time is None:
            current_epoch_time = dt
            current_epoch = [r]
            continue
        diff_min = abs((current_epoch_time - dt).total_seconds()) / 60.0
        if diff_min <= tolerance_min:
            current_epoch.append(r)
        else:
            if current_epoch:
                epochs.append(current_epoch)
            current_epoch_time = dt
            current_epoch = [r]
    if current_epoch:
        epochs.append(current_epoch)

    coverage_sets: List[CoverageSet] = []
    for ep in epochs:
        footprints = []
        scene_ids: List[int] = []
        scene_uris: List[str] = []
        epoch_time_str = str(ep[0]["acquired_at"])
        for r in ep:
            try:
                fp = json.loads(r["footprint_geojson"]) if isinstance(r["footprint_geojson"], str) else r["footprint_geojson"]
                footprints.append(fp)
                if r.get("id") is not None:
                    scene_ids.append(int(r["id"]))
                scene_uris.append(str(r["uri"]))
            except Exception:
                continue
        if not footprints:
            continue
        try:
            combined = unary_union([extract_boundary_geometry(fp) for fp in footprints])
            if not boundary_geom.intersects(combined):
                continue
            intersection = boundary_geom.intersection(combined)
            coverage = (intersection.area / boundary_geom.area) * 100.0
        except Exception:
            continue
        if coverage >= min_epoch_cov:
            coverage_sets.append(
                CoverageSet(
                    epoch_time=epoch_time_str,
                    scene_ids=scene_ids,
                    scene_uris=scene_uris,
                    coverage_percent=coverage,
                )
            )

    return coverage_sets
