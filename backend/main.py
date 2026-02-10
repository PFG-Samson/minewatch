from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from io import BytesIO
from typing import Any, Optional
from urllib.request import Request, urlopen

from contextlib import asynccontextmanager
import uvicorn
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from backend.analysis_pipeline import ImageryScene, run_analysis
from backend.utils.imagery_utils import generate_rgb_png, CACHE_DIR

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    init_db()
    yield
    # Shutdown logic (optional)
    pass


app = FastAPI(
    title="MineWatch API", 
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = Path(__file__).parent / "minewatch.db"

# Ensure cache dir exists and mount it
CACHE_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/data/cache", StaticFiles(directory=CACHE_DIR), name="cache")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_db() -> sqlite3.Connection:
    # Use timeout and check_same_thread to handle concurrent requests better
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrent access
    conn.execute("PRAGMA journal_mode=WAL")
    # Set busy timeout
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def init_db() -> None:
    conn = get_db()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS imagery_scene (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                acquired_at TEXT NOT NULL,
                cloud_cover REAL,
                footprint_geojson TEXT,
                uri TEXT,
                created_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mine_area (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                name TEXT NOT NULL,
                description TEXT,
                boundary_geojson TEXT NOT NULL,
                buffer_km REAL NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_run (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                baseline_date TEXT,
                latest_date TEXT,
                baseline_scene_id INTEGER,
                latest_scene_id INTEGER,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        existing_cols = {
            r["name"] for r in conn.execute("PRAGMA table_info(analysis_run)").fetchall()
        }
        if "baseline_scene_id" not in existing_cols:
            conn.execute("ALTER TABLE analysis_run ADD COLUMN baseline_scene_id INTEGER")
        if "latest_scene_id" not in existing_cols:
            conn.execute("ALTER TABLE analysis_run ADD COLUMN latest_scene_id INTEGER")

        mine_cols = {
            r["name"] for r in conn.execute("PRAGMA table_info(mine_area)").fetchall()
        }
        if "description" not in mine_cols:
            conn.execute("ALTER TABLE mine_area ADD COLUMN description TEXT")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_zone (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                zone_type TEXT NOT NULL,
                area_ha REAL NOT NULL,
                geometry_geojson TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES analysis_run(id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alert (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                alert_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                location TEXT NOT NULL,
                severity TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES analysis_run(id)
            )
            """
        )

        conn.commit()
    finally:
        conn.close()


@app.get("/analysis-runs/{run_id}/report")
def get_analysis_report(run_id: int) -> Response:
    conn = get_db()
    try:
        run = conn.execute("SELECT * FROM analysis_run WHERE id = ?", (run_id,)).fetchone()
        if run is None:
            raise HTTPException(status_code=404, detail="Analysis run not found")

        zones = conn.execute(
            "SELECT zone_type, area_ha FROM analysis_zone WHERE run_id = ?",
            (run_id,),
        ).fetchall()

        alerts = conn.execute(
            """
            SELECT alert_type, title, severity, created_at
            FROM alert
            WHERE run_id = ?
            ORDER BY created_at DESC
            """,
            (run_id,),
        ).fetchall()

        totals: dict[str, float] = {}
        for z in zones:
            zt = str(z["zone_type"])
            totals[zt] = totals.get(zt, 0.0) + float(z["area_ha"])

        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        width, height = A4
        x = 18 * mm
        y = height - 18 * mm

        def draw_line(text: str, dy: float = 6.5 * mm, font: str = "Helvetica", size: int = 11) -> None:
            nonlocal y
            c.setFont(font, size)
            c.drawString(x, y, text)
            y -= dy

        draw_line("MineWatch – Environmental Change Report", dy=9 * mm, font="Helvetica-Bold", size=16)
        draw_line(f"Run ID: {int(run['id'])}")
        draw_line(f"Created (UTC): {run['created_at']}")
        draw_line(f"Baseline date: {run['baseline_date'] or 'n/a'}")
        draw_line(f"Latest date: {run['latest_date'] or 'n/a'}")
        draw_line(f"Status: {run['status']}", dy=10 * mm)

        draw_line("Summary (Area by class)", dy=8 * mm, font="Helvetica-Bold", size=13)
        if not totals:
            draw_line("No zones available.")
        else:
            for key in sorted(totals.keys()):
                draw_line(f"- {key.replace('_', ' ').title()}: {totals[key]:.2f} hectares")

        y -= 4 * mm
        draw_line("Alerts", dy=8 * mm, font="Helvetica-Bold", size=13)
        if not alerts:
            draw_line("No alerts generated for this run.")
        else:
            for a in alerts[:12]:
                draw_line(f"- [{a['severity'].upper()}] {a['title']} ({a['created_at']})", size=10)

        y -= 6 * mm
        draw_line("Notes", dy=8 * mm, font="Helvetica-Bold", size=13)
        draw_line("This report is generated automatically based on satellite-derived change detection.", size=10)
        draw_line("Use this document as supporting evidence for compliance checks and ESG reporting.", size=10)

        c.showPage()
        c.save()

        pdf_bytes = buf.getvalue()
        filename = f"minewatch-report-run-{run_id}.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    finally:
        conn.close()


@app.get("/analysis-runs/{run_id}/imagery")
def get_run_imagery(run_id: int) -> dict[str, Any]:
    """Returns the RGB preview URLs and bounds for the baseline and latest scenes in a run."""
    conn = get_db()
    try:
        run = conn.execute("SELECT baseline_scene_id, latest_scene_id FROM analysis_run WHERE id = ?", (run_id,)).fetchone()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        def get_scene_preview(scene_id: Optional[int], label: str):
            if not scene_id:
                return None
            scene = conn.execute("SELECT uri FROM imagery_scene WHERE id = ?", (scene_id,)).fetchone()
            if not scene:
                return None
            
            uri = scene["uri"]
            # These paths assume the downloader has already run
            base_dir = Path(__file__).parent / "data" / "imagery"
            red = base_dir / f"{uri}_B04.tif"
            green = base_dir / f"{uri}_B03.tif"
            blue = base_dir / f"{uri}_B02.tif"
            
            if red.exists() and green.exists() and blue.exists():
                return generate_rgb_png(str(red), str(green), str(blue), f"preview_{uri}")
            return None

        return {
            "baseline": get_scene_preview(run["baseline_scene_id"], "baseline"),
            "latest": get_scene_preview(run["latest_scene_id"], "latest")
        }
    finally:
        conn.close()


class MineAreaUpsert(BaseModel):
    name: str = Field(default="Mine Area")
    description: Optional[str] = None
    boundary: dict[str, Any]
    buffer_km: float = Field(default=2.0, ge=0.0)


class MineAreaOut(BaseModel):
    name: str
    description: Optional[str] = None
    boundary: dict[str, Any]
    buffer_km: float
    created_at: str
    updated_at: str


class AnalysisRunCreate(BaseModel):
    baseline_date: Optional[str] = None
    latest_date: Optional[str] = None
    baseline_scene_id: Optional[int] = None
    latest_scene_id: Optional[int] = None


class AnalysisRunOut(BaseModel):
    id: int
    baseline_date: Optional[str]
    latest_date: Optional[str]
    baseline_scene_id: Optional[int] = None
    latest_scene_id: Optional[int] = None
    status: str
    created_at: str


class ImagerySceneCreate(BaseModel):
    source: str = Field(default="Sentinel-2")
    acquired_at: str
    cloud_cover: Optional[float] = None
    footprint: Optional[dict[str, Any]] = None
    uri: Optional[str] = None


class ImagerySceneOut(BaseModel):
    id: int
    source: str
    acquired_at: str
    cloud_cover: Optional[float] = None
    footprint: Optional[dict[str, Any]] = None
    uri: Optional[str] = None
    created_at: str


class StacIngestJobCreate(BaseModel):
    collection: str = Field(default="sentinel-2-l2a")
    max_items: int = Field(default=10, ge=1, le=100)
    cloud_cover_lte: Optional[float] = Field(default=20.0, ge=0.0, le=100.0)


class AlertOut(BaseModel):
    id: int
    run_id: Optional[int]
    type: str
    title: str
    description: str
    location: str
    severity: str
    created_at: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/mine-area", response_model=MineAreaOut)
def get_mine_area() -> MineAreaOut:
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM mine_area WHERE id = 1").fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Mine area not configured")

        return MineAreaOut(
            name=row["name"],
            description=row["description"],
            boundary=json.loads(row["boundary_geojson"]),
            buffer_km=float(row["buffer_km"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
    finally:
        conn.close()


@app.put("/mine-area", response_model=MineAreaOut)
def upsert_mine_area(payload: MineAreaUpsert) -> MineAreaOut:
    now = _utc_now_iso()
    conn = get_db()
    try:
        existing = conn.execute("SELECT * FROM mine_area WHERE id = 1").fetchone()
        if existing is None:
            conn.execute(
                """
                INSERT INTO mine_area (id, name, description, boundary_geojson, buffer_km, created_at, updated_at)
                VALUES (1, ?, ?, ?, ?, ?, ?)
                """,
                (payload.name, payload.description, json.dumps(payload.boundary), payload.buffer_km, now, now),
            )
        else:
            conn.execute(
                """
                UPDATE mine_area
                SET name = ?, description = ?, boundary_geojson = ?, buffer_km = ?, updated_at = ?
                WHERE id = 1
                """,
                (payload.name, payload.description, json.dumps(payload.boundary), payload.buffer_km, now),
            )

        conn.commit()

        row = conn.execute("SELECT * FROM mine_area WHERE id = 1").fetchone()
        if row is None:
            raise HTTPException(status_code=500, detail="Failed to save mine area")

        return MineAreaOut(
            name=row["name"],
            boundary=json.loads(row["boundary_geojson"]),
            buffer_km=float(row["buffer_km"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
    finally:
        conn.close()


@app.post("/analysis-runs", response_model=AnalysisRunOut)
def create_analysis_run(payload: AnalysisRunCreate) -> AnalysisRunOut:
    conn = get_db()
    try:
        now = _utc_now_iso()

        baseline_scene_id = payload.baseline_scene_id
        latest_scene_id = payload.latest_scene_id
        if baseline_scene_id is None or latest_scene_id is None:
            rows = conn.execute(
                """
                SELECT id
                FROM imagery_scene
                ORDER BY acquired_at DESC
                LIMIT 2
                """
            ).fetchall()

            if latest_scene_id is None and len(rows) >= 1:
                latest_scene_id = int(rows[0]["id"])
            if baseline_scene_id is None and len(rows) >= 2:
                baseline_scene_id = int(rows[1]["id"])

        cur = conn.execute(
            """
            INSERT INTO analysis_run (baseline_date, latest_date, baseline_scene_id, latest_scene_id, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (payload.baseline_date, payload.latest_date, baseline_scene_id, latest_scene_id, "completed", now),
        )
        run_id = int(cur.lastrowid)

        mine_row = conn.execute("SELECT boundary_geojson, buffer_km FROM mine_area WHERE id = 1").fetchone()
        mine_area = None
        if mine_row is not None:
            mine_area = {
                "boundary": json.loads(mine_row["boundary_geojson"]),
                "buffer_km": float(mine_row["buffer_km"]),
            }

        baseline_scene = None
        latest_scene = None
        if baseline_scene_id is not None:
            s = conn.execute(
                "SELECT id, source, acquired_at, cloud_cover, uri FROM imagery_scene WHERE id = ?",
                (baseline_scene_id,),
            ).fetchone()
            if s is not None:
                baseline_scene = ImageryScene(
                    id=int(s["id"]),
                    source=s["source"],
                    acquired_at=s["acquired_at"],
                    cloud_cover=float(s["cloud_cover"]) if s["cloud_cover"] is not None else None,
                    uri=s["uri"],
                )
        if latest_scene_id is not None:
            s = conn.execute(
                "SELECT id, source, acquired_at, cloud_cover, uri FROM imagery_scene WHERE id = ?",
                (latest_scene_id,),
            ).fetchone()
            if s is not None:
                latest_scene = ImageryScene(
                    id=int(s["id"]),
                    source=s["source"],
                    acquired_at=s["acquired_at"],
                    cloud_cover=float(s["cloud_cover"]) if s["cloud_cover"] is not None else None,
                    uri=s["uri"],
                )

        zones, alerts = run_analysis(
            mine_area=mine_area,
            baseline_date=payload.baseline_date,
            latest_date=payload.latest_date,
            baseline_scene=baseline_scene,
            latest_scene=latest_scene,
        )

        for z in zones:
            conn.execute(
                """
                INSERT INTO analysis_zone (run_id, zone_type, area_ha, geometry_geojson)
                VALUES (?, ?, ?, ?)
                """,
                (run_id, z.zone_type, z.area_ha, json.dumps(z.geometry)),
            )

        for a in alerts:
            conn.execute(
                """
                INSERT INTO alert (run_id, alert_type, title, description, location, severity, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (run_id, a.alert_type, a.title, a.description, a.location, a.severity, now),
            )

        conn.commit()

        row = conn.execute("SELECT * FROM analysis_run WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=500, detail="Failed to create analysis run")

        return AnalysisRunOut(
            id=int(row["id"]),
            baseline_date=row["baseline_date"],
            latest_date=row["latest_date"],
            baseline_scene_id=row["baseline_scene_id"],
            latest_scene_id=row["latest_scene_id"],
            status=row["status"],
            created_at=row["created_at"],
        )
    finally:
        conn.close()


def _bbox_from_geojson(obj: dict[str, Any]) -> Optional[list[float]]:
    def iter_coords(node: Any):
        if isinstance(node, (list, tuple)):
            if len(node) == 2 and all(isinstance(x, (int, float)) for x in node):
                yield float(node[0]), float(node[1])
            else:
                for item in node:
                    yield from iter_coords(item)

    geometry = None
    if obj.get("type") == "FeatureCollection":
        features = obj.get("features") or []
        if features:
            geometry = features[0].get("geometry")
    elif obj.get("type") == "Feature":
        geometry = obj.get("geometry")
    else:
        geometry = obj

    if not isinstance(geometry, dict) or "coordinates" not in geometry:
        return None

    xs: list[float] = []
    ys: list[float] = []
    for x, y in iter_coords(geometry.get("coordinates")):
        xs.append(x)
        ys.append(y)
    if not xs or not ys:
        return None
    return [min(xs), min(ys), max(xs), max(ys)]


def _stac_search(*, bbox: list[float], collection: str, max_items: int, cloud_cover_lte: Optional[float]) -> dict[str, Any]:
    url = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
    body: dict[str, Any] = {
        "collections": [collection],
        "bbox": bbox,
        "limit": max_items,
    }
    if cloud_cover_lte is not None:
        body["query"] = {"eo:cloud_cover": {"lte": cloud_cover_lte}}

    resp = requests.post(url, json=body, timeout=30)
    resp.raise_for_status()
    return resp.json()


@app.post("/jobs/ingest-stac", response_model=list[ImagerySceneOut])
def ingest_stac_job(payload: StacIngestJobCreate) -> list[ImagerySceneOut]:
    conn = get_db()
    try:
        mine = conn.execute("SELECT boundary_geojson FROM mine_area WHERE id = 1").fetchone()
        if mine is None:
            raise HTTPException(status_code=400, detail="Mine area not configured")

        boundary = json.loads(mine["boundary_geojson"])
        bbox = _bbox_from_geojson(boundary)
        if bbox is None:
            raise HTTPException(status_code=400, detail="Unable to derive bbox from boundary GeoJSON")

        search = _stac_search(
            bbox=bbox,
            collection=payload.collection,
            max_items=payload.max_items,
            cloud_cover_lte=payload.cloud_cover_lte,
        )

        features = search.get("features") or []
        if not features:
            conn.commit()
            return []

        now = _utc_now_iso()
        created: list[ImagerySceneOut] = []

        for item in features:
            props = item.get("properties") or {}
            acquired_at = props.get("datetime") or props.get("start_datetime") or now
            cloud = props.get("eo:cloud_cover")
            uri = item.get("id")
            footprint = item.get("geometry")

            # Check if scene already exists to avoid duplicates
            existing = conn.execute("SELECT id FROM imagery_scene WHERE uri = ?", (str(uri),)).fetchone()
            if existing:
                continue

            cur = conn.execute(
                """
                INSERT INTO imagery_scene (source, acquired_at, cloud_cover, footprint_geojson, uri, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.collection,
                    str(acquired_at),
                    float(cloud) if cloud is not None else None,
                    json.dumps(footprint) if footprint is not None else None,
                    str(uri) if uri is not None else None,
                    now,
                ),
            )
            scene_id = int(cur.lastrowid)
            row = conn.execute(
                "SELECT id, source, acquired_at, cloud_cover, footprint_geojson, uri, created_at FROM imagery_scene WHERE id = ?",
                (scene_id,),
            ).fetchone()
            if row is None:
                continue
            created.append(
                ImagerySceneOut(
                    id=int(row["id"]),
                    source=row["source"],
                    acquired_at=row["acquired_at"],
                    cloud_cover=float(row["cloud_cover"]) if row["cloud_cover"] is not None else None,
                    footprint=json.loads(row["footprint_geojson"]) if row["footprint_geojson"] is not None else None,
                    uri=row["uri"],
                    created_at=row["created_at"],
                )
            )

        conn.commit()
        return created
    except Exception as e:
        print(f"STAC Ingest Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.post("/imagery", response_model=ImagerySceneOut)
def create_imagery_scene(payload: ImagerySceneCreate) -> ImagerySceneOut:
    conn = get_db()
    try:
        now = _utc_now_iso()
        cur = conn.execute(
            """
            INSERT INTO imagery_scene (source, acquired_at, cloud_cover, footprint_geojson, uri, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                payload.source,
                payload.acquired_at,
                payload.cloud_cover,
                json.dumps(payload.footprint) if payload.footprint is not None else None,
                payload.uri,
                now,
            ),
        )
        scene_id = int(cur.lastrowid)
        conn.commit()

        row = conn.execute("SELECT * FROM imagery_scene WHERE id = ?", (scene_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=500, detail="Failed to create imagery scene")

        return ImagerySceneOut(
            id=int(row["id"]),
            source=row["source"],
            acquired_at=row["acquired_at"],
            cloud_cover=float(row["cloud_cover"]) if row["cloud_cover"] is not None else None,
            footprint=json.loads(row["footprint_geojson"]) if row["footprint_geojson"] is not None else None,
            uri=row["uri"],
            created_at=row["created_at"],
        )
    finally:
        conn.close()


@app.get("/imagery", response_model=list[ImagerySceneOut])
def list_imagery_scenes(limit: int = 50) -> list[ImagerySceneOut]:
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT id, source, acquired_at, cloud_cover, footprint_geojson, uri, created_at
            FROM imagery_scene
            ORDER BY acquired_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        out: list[ImagerySceneOut] = []
        for r in rows:
            out.append(
                ImagerySceneOut(
                    id=int(r["id"]),
                    source=r["source"],
                    acquired_at=r["acquired_at"],
                    cloud_cover=float(r["cloud_cover"]) if r["cloud_cover"] is not None else None,
                    footprint=json.loads(r["footprint_geojson"]) if r["footprint_geojson"] is not None else None,
                    uri=r["uri"],
                    created_at=r["created_at"],
                )
            )
        return out
    finally:
        conn.close()


@app.get("/imagery/latest", response_model=ImagerySceneOut)
def get_latest_imagery_scene() -> ImagerySceneOut:
    conn = get_db()
    try:
        row = conn.execute(
            """
            SELECT id, source, acquired_at, cloud_cover, footprint_geojson, uri, created_at
            FROM imagery_scene
            ORDER BY acquired_at DESC
            LIMIT 1
            """
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="No imagery scenes available")

        return ImagerySceneOut(
            id=int(row["id"]),
            source=row["source"],
            acquired_at=row["acquired_at"],
            cloud_cover=float(row["cloud_cover"]) if row["cloud_cover"] is not None else None,
            footprint=json.loads(row["footprint_geojson"]) if row["footprint_geojson"] is not None else None,
            uri=row["uri"],
            created_at=row["created_at"],
        )
    finally:
        conn.close()


@app.get("/analysis-runs/{run_id}")
def get_analysis_run(run_id: int) -> dict[str, Any]:
    conn = get_db()
    try:
        run = conn.execute("SELECT * FROM analysis_run WHERE id = ?", (run_id,)).fetchone()
        if run is None:
            raise HTTPException(status_code=404, detail="Analysis run not found")

        zones = conn.execute(
            "SELECT id, zone_type, area_ha, geometry_geojson FROM analysis_zone WHERE run_id = ?",
            (run_id,),
        ).fetchall()

        features = []
        for z in zones:
            features.append(
                {
                    "type": "Feature",
                    "id": int(z["id"]),
                    "properties": {
                        "zone_type": z["zone_type"],
                        "area_ha": float(z["area_ha"]),
                    },
                    "geometry": json.loads(z["geometry_geojson"]),
                }
            )

        return {
            "run": {
                "id": int(run["id"]),
                "baseline_date": run["baseline_date"],
                "latest_date": run["latest_date"],
                "status": run["status"],
                "created_at": run["created_at"],
            },
            "zones": {"type": "FeatureCollection", "features": features},
        }
    finally:
        conn.close()


@app.get("/analysis-runs", response_model=list[AnalysisRunOut])
def list_analysis_runs(limit: int = 50) -> list[AnalysisRunOut]:
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT id, baseline_date, latest_date, baseline_scene_id, latest_scene_id, status, created_at
            FROM analysis_run
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        return [
            AnalysisRunOut(
                id=int(r["id"]),
                baseline_date=r["baseline_date"],
                latest_date=r["latest_date"],
                baseline_scene_id=r["baseline_scene_id"],
                latest_scene_id=r["latest_scene_id"],
                status=r["status"],
                created_at=r["created_at"],
            )
            for r in rows
        ]
    finally:
        conn.close()


@app.get("/alerts", response_model=list[AlertOut])
def list_alerts(limit: int = 50) -> list[AlertOut]:
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT id, run_id, alert_type, title, description, location, severity, created_at
            FROM alert
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        return [
            AlertOut(
                id=int(r["id"]),
                run_id=int(r["run_id"]) if r["run_id"] is not None else None,
                type=r["alert_type"],
                title=r["title"],
                description=r["description"],
                location=r["location"],
                severity=r["severity"],
                created_at=r["created_at"],
            )
            for r in rows
        ]
    finally:
        conn.close()


@app.get("/imagery/scenes")
def list_imagery_scenes_simple(limit: int = 20) -> list[dict[str, Any]]:
    """Simplified scene listing for UI dropdowns with essential metadata"""
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT id, source, acquired_at, cloud_cover, uri, created_at
            FROM imagery_scene
            ORDER BY acquired_at DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

        return [
            {
                "id": int(row["id"]),
                "source": row["source"],
                "acquired_at": row["acquired_at"],
                "cloud_cover": float(row["cloud_cover"]) if row["cloud_cover"] is not None else None,
                "uri": row["uri"],
                "created_at": row["created_at"]
            }
            for row in rows
        ]
    finally:
        conn.close()


@app.get("/alert-rules")
def get_alert_rules() -> dict[str, Any]:
    """Get current alert rule configuration"""
    from backend.alert_rules import AlertRuleEngine
    
    engine = AlertRuleEngine()
    return engine.get_config()


class AlertRulesUpdate(BaseModel):
    """Model for updating alert rules configuration"""
    rules: dict[str, Any]
    global_settings: Optional[dict[str, Any]] = None


@app.put("/alert-rules")
def update_alert_rules(payload: AlertRulesUpdate) -> dict[str, str]:
    """
    Update alert rule configuration.
    
    This endpoint allows administrators to modify alert thresholds,
    enable/disable specific rules, and adjust severity levels.
    """
    from backend.alert_rules import AlertRuleEngine
    
    engine = AlertRuleEngine()
    
    # Build new config
    new_config = {
        "version": "1.0",
        "rules": payload.rules
    }
    
    if payload.global_settings:
        new_config["global_settings"] = payload.global_settings
    
    # Update and reload
    engine.update_config(new_config)
    
    return {"status": "success", "message": "Alert rules updated successfully"}


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
