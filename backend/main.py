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
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles
import zipfile
import xml.etree.ElementTree as ET
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from backend.analysis_pipeline import ImageryScene, run_analysis
from backend.utils.imagery_utils import generate_rgb_png, CACHE_DIR
from backend.exceptions import (
    InsufficientCoverageError,
    MosaicError,
    IdenticalScenesError,
    DatabaseConnectionError,
    AnalysisError,
    MineWatchError
)

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
                geometry_geojson TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES analysis_run(id)
            )
            """
        )

        # Migration: Add geometry_geojson column if it doesn't exist
        alert_cols = {
            r["name"] for r in conn.execute("PRAGMA table_info(alert)").fetchall()
        }
        if "geometry_geojson" not in alert_cols:
            conn.execute("ALTER TABLE alert ADD COLUMN geometry_geojson TEXT")

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
        
        # Get mine area information
        mine_area = conn.execute("SELECT name, description FROM mine_area WHERE id = 1").fetchone()
        mine_name = mine_area["name"] if mine_area else "Mine Site"
        mine_description = mine_area["description"] if mine_area and mine_area["description"] else None

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

        # Header with mine name
        draw_line("MineWatch – Environmental Change Report", dy=9 * mm, font="Helvetica-Bold", size=16)
        draw_line(f"Site: {mine_name}", dy=7 * mm, font="Helvetica-Bold", size=13)
        
        # Add description if available
        if mine_description:
            # Word wrap description if too long
            max_chars = 85
            if len(mine_description) > max_chars:
                desc_lines = [mine_description[i:i+max_chars] for i in range(0, len(mine_description), max_chars)]
                for desc_line in desc_lines[:2]:  # Max 2 lines
                    draw_line(desc_line, dy=5.5 * mm, font="Helvetica-Oblique", size=10)
            else:
                draw_line(mine_description, dy=6 * mm, font="Helvetica-Oblique", size=10)
        
        y -= 3 * mm  # Extra spacing
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
        # Include mine name in filename (sanitized)
        safe_mine_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in mine_name)
        safe_mine_name = safe_mine_name.replace(' ', '-').lower()[:30]  # Max 30 chars
        filename = f"minewatch-{safe_mine_name}-run-{run_id}.pdf"

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
            base_dir = Path(__file__).parent / "data" / "imagery"
            red = base_dir / f"{uri}_B04.tif"
            green = base_dir / f"{uri}_B03.tif"
            blue = base_dir / f"{uri}_B02.tif"
            
            if red.exists() and green.exists() and blue.exists():
                return generate_rgb_png(str(red), str(green), str(blue), f"preview_{uri}")
            mosaic_dir = Path(__file__).parent / "data" / "mosaics"
            m_prefix = f"run{run_id}_{label.lower()}"
            m_red = mosaic_dir / f"{m_prefix}_B04_clipped.tif"
            m_green = mosaic_dir / f"{m_prefix}_B03_clipped.tif"
            m_blue = mosaic_dir / f"{m_prefix}_B02_clipped.tif"
            if m_red.exists() and m_green.exists() and m_blue.exists():
                return generate_rgb_png(str(m_red), str(m_green), str(m_blue), f"preview_{m_prefix}")
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
    area_ha: float = 0.0


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
    max_items: int = Field(default=50, ge=1, le=200)  # Increased for multi-tile coverage
    cloud_cover_lte: Optional[float] = Field(default=20.0, ge=0.0, le=100.0)
    ensure_coverage: bool = Field(default=True)  # Keep fetching until boundary is covered
    min_coverage_percent: float = Field(default=95.0, ge=50.0, le=100.0)


class AlertOut(BaseModel):
    id: int
    run_id: Optional[int]
    type: str
    title: str
    description: str
    location: str
    severity: str
    geometry: Optional[dict[str, Any]] = None
    created_at: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _parse_kml_coordinates(coord_string: str) -> list[list[float]]:
    """
    Parse KML coordinate string into list of [lon, lat] or [lon, lat, alt] arrays.
    KML format: "lon,lat,alt lon,lat,alt ..." (space-separated, comma within)
    """
    coords = []
    # Split by whitespace and filter empty strings
    parts = coord_string.strip().split()
    for part in parts:
        if not part.strip():
            continue
        values = part.split(',')
        if len(values) >= 2:
            try:
                lon = float(values[0])
                lat = float(values[1])
                coords.append([lon, lat])
            except ValueError:
                continue
    return coords


def _kml_to_geojson(kml_content: str) -> dict[str, Any]:
    """
    Convert KML content to GeoJSON.
    Supports: Point, LineString, Polygon, MultiGeometry.
    """
    # KML namespaces
    namespaces = {
        'kml': 'http://www.opengis.net/kml/2.2',
        'gx': 'http://www.google.com/kml/ext/2.2',
    }
    
    # Also try without namespace for older KML files
    try:
        root = ET.fromstring(kml_content)
    except ET.ParseError as e:
        raise ValueError(f"Invalid KML XML: {e}")
    
    features = []
    
    # Find all Placemarks (with or without namespace)
    placemarks = root.findall('.//{http://www.opengis.net/kml/2.2}Placemark')
    if not placemarks:
        placemarks = root.findall('.//Placemark')
    
    for placemark in placemarks:
        # Get name
        name_elem = placemark.find('{http://www.opengis.net/kml/2.2}name')
        if name_elem is None:
            name_elem = placemark.find('name')
        name = name_elem.text if name_elem is not None else "Unnamed"
        
        # Get description
        desc_elem = placemark.find('{http://www.opengis.net/kml/2.2}description')
        if desc_elem is None:
            desc_elem = placemark.find('description')
        description = desc_elem.text if desc_elem is not None else ""
        
        geometry = None
        
        # Try to find Polygon
        polygon = placemark.find('.//{http://www.opengis.net/kml/2.2}Polygon')
        if polygon is None:
            polygon = placemark.find('.//Polygon')
        
        if polygon is not None:
            outer = polygon.find('.//{http://www.opengis.net/kml/2.2}outerBoundaryIs//{http://www.opengis.net/kml/2.2}coordinates')
            if outer is None:
                outer = polygon.find('.//outerBoundaryIs//coordinates')
            
            if outer is not None and outer.text:
                coords = _parse_kml_coordinates(outer.text)
                if coords:
                    # GeoJSON Polygon needs nested array
                    geometry = {
                        "type": "Polygon",
                        "coordinates": [coords]
                    }
        
        # Try to find LineString
        if geometry is None:
            linestring = placemark.find('.//{http://www.opengis.net/kml/2.2}LineString')
            if linestring is None:
                linestring = placemark.find('.//LineString')
            
            if linestring is not None:
                coords_elem = linestring.find('{http://www.opengis.net/kml/2.2}coordinates')
                if coords_elem is None:
                    coords_elem = linestring.find('coordinates')
                
                if coords_elem is not None and coords_elem.text:
                    coords = _parse_kml_coordinates(coords_elem.text)
                    if coords:
                        geometry = {
                            "type": "LineString",
                            "coordinates": coords
                        }
        
        # Try to find Point
        if geometry is None:
            point = placemark.find('.//{http://www.opengis.net/kml/2.2}Point')
            if point is None:
                point = placemark.find('.//Point')
            
            if point is not None:
                coords_elem = point.find('{http://www.opengis.net/kml/2.2}coordinates')
                if coords_elem is None:
                    coords_elem = point.find('coordinates')
                
                if coords_elem is not None and coords_elem.text:
                    coords = _parse_kml_coordinates(coords_elem.text)
                    if coords:
                        geometry = {
                            "type": "Point",
                            "coordinates": coords[0]
                        }
        
        if geometry:
            features.append({
                "type": "Feature",
                "properties": {
                    "name": name,
                    "description": description
                },
                "geometry": geometry
            })
    
    if not features:
        raise ValueError("No valid geometries found in KML file")
    
    return {
        "type": "FeatureCollection",
        "features": features
    }


@app.post("/convert-boundary")
async def convert_boundary_file(file: UploadFile = File(...)) -> dict[str, Any]:
    """
    Convert uploaded boundary file to GeoJSON.
    
    Supports:
    - .geojson, .json (passed through with validation)
    - .kml (converted to GeoJSON)
    - .kmz (unzipped, then KML converted to GeoJSON)
    
    Returns:
        GeoJSON FeatureCollection or Geometry
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    filename = file.filename.lower()
    content = await file.read()
    
    try:
        # Handle GeoJSON files
        if filename.endswith('.geojson') or filename.endswith('.json'):
            try:
                geojson = json.loads(content.decode('utf-8'))
                # Validate it looks like GeoJSON
                if not isinstance(geojson, dict):
                    raise ValueError("Not a valid GeoJSON object")
                if 'type' not in geojson:
                    raise ValueError("Missing 'type' field in GeoJSON")
                return {
                    "success": True,
                    "format": "geojson",
                    "geojson": geojson
                }
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
        
        # Handle KMZ files (zipped KML)
        elif filename.endswith('.kmz'):
            try:
                with zipfile.ZipFile(BytesIO(content)) as zf:
                    # Find the KML file inside (usually doc.kml)
                    kml_files = [f for f in zf.namelist() if f.lower().endswith('.kml')]
                    if not kml_files:
                        raise ValueError("No KML file found inside KMZ archive")
                    
                    # Read the first KML file
                    kml_content = zf.read(kml_files[0]).decode('utf-8')
                    geojson = _kml_to_geojson(kml_content)
                    return {
                        "success": True,
                        "format": "kmz",
                        "source_file": kml_files[0],
                        "geojson": geojson
                    }
            except zipfile.BadZipFile:
                raise HTTPException(status_code=400, detail="Invalid KMZ file (not a valid ZIP archive)")
        
        # Handle KML files
        elif filename.endswith('.kml'):
            try:
                kml_content = content.decode('utf-8')
                geojson = _kml_to_geojson(kml_content)
                return {
                    "success": True,
                    "format": "kml",
                    "geojson": geojson
                }
            except UnicodeDecodeError:
                raise HTTPException(status_code=400, detail="KML file is not valid UTF-8 text")
        
        else:
            supported = ".geojson, .json, .kml, .kmz"
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file format. Supported: {supported}"
            )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error converting boundary file: {e}")
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")


@app.get("/mine-area", response_model=MineAreaOut)
def get_mine_area() -> MineAreaOut:
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM mine_area WHERE id = 1").fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Mine area not configured")

        boundary = json.loads(row["boundary_geojson"])
        
        # Calculate area in hectares
        from shapely.geometry import shape
        
        # Handle both FeatureCollection and direct geometry
        if boundary.get("type") == "FeatureCollection":
            # Extract the first feature's geometry
            if boundary.get("features") and len(boundary["features"]) > 0:
                geom_data = boundary["features"][0]["geometry"]
            else:
                raise HTTPException(status_code=400, detail="FeatureCollection has no features")
        elif boundary.get("type") == "Feature":
            # Extract geometry from Feature
            geom_data = boundary["geometry"]
        else:
            # Direct geometry (Polygon, MultiPolygon, etc.)
            geom_data = boundary
        
        geom = shape(geom_data)
        # Area in square degrees, convert to hectares (approximate)
        # 1 degree ≈ 111.32 km at equator
        area_sq_deg = geom.area
        area_sq_m = area_sq_deg * (111319.9 ** 2)  # Convert to square meters
        area_ha = area_sq_m / 10000  # Convert to hectares

        return MineAreaOut(
            name=row["name"] if row["name"] else "Mine Area",
            description=row["description"] if row["description"] else None,
            boundary=boundary,
            buffer_km=float(row["buffer_km"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            area_ha=area_ha,
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
            name=row["name"] if row["name"] else "Mine Area",
            description=row["description"] if row["description"] else None,
            boundary=json.loads(row["boundary_geojson"]),
            buffer_km=float(row["buffer_km"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            area_ha=0.0,
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

        # Get mine name for logging
        mine_name = None
        if mine_area:
            name_row = conn.execute("SELECT name FROM mine_area WHERE id = 1").fetchone()
            if name_row:
                mine_name = name_row["name"]
                mine_area["name"] = mine_name

        try:
            zones, alerts = run_analysis(
                mine_area=mine_area,
                baseline_date=payload.baseline_date,
                latest_date=payload.latest_date,
                baseline_scene=baseline_scene,
                latest_scene=latest_scene,
                run_id=run_id,
                save_indices=True,
                db_conn=conn,  # Pass connection for multi-scene mosaicking
            )
        except InsufficientCoverageError as e:
            # Handle coverage errors with detailed user message
            conn.execute(
                "UPDATE analysis_run SET status = ? WHERE id = ?",
                ("failed_coverage", run_id)
            )
            conn.commit()
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "insufficient_coverage",
                    "message": e.get_user_message() if hasattr(e, 'get_user_message') else str(e),
                    "coverage_percent": e.coverage_percent,
                    "required_percent": e.required_percent,
                    "run_id": run_id
                }
            )
        except IdenticalScenesError as e:
            # Handle identical scenes error
            conn.execute(
                "UPDATE analysis_run SET status = ? WHERE id = ?",
                ("failed_identical_scenes", run_id)
            )
            conn.commit()
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "identical_scenes",
                    "message": str(e),
                    "run_id": run_id
                }
            )
        except MosaicError as e:
            # Handle mosaic errors
            conn.execute(
                "UPDATE analysis_run SET status = ? WHERE id = ?",
                ("failed_mosaic", run_id)
            )
            conn.commit()
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "mosaic_failed",
                    "message": str(e),
                    "band": e.band_name if hasattr(e, 'band_name') else None,
                    "run_id": run_id
                }
            )
        except (DatabaseConnectionError, AnalysisError, MineWatchError) as e:
            # Handle other known errors
            conn.execute(
                "UPDATE analysis_run SET status = ? WHERE id = ?",
                ("failed", run_id)
            )
            conn.commit()
            raise HTTPException(
                status_code=500,
                detail={
                    "error": type(e).__name__,
                    "message": str(e),
                    "run_id": run_id
                }
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
                INSERT INTO alert (run_id, alert_type, title, description, location, severity, geometry_geojson, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (run_id, a.alert_type, a.title, a.description, a.location, a.severity,
                 json.dumps(a.geometry) if a.geometry else None, now),
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
    """
    Extract bounding box from any GeoJSON structure.
    
    Handles:
    - Geometry types: Point, LineString, Polygon, Multi*, GeometryCollection
    - Feature and FeatureCollection wrappers
    - 2D, 3D, and 4D coordinates [lon, lat, elevation, measure]
    - String coordinates (converts to float)
    - Null/empty geometries (skips gracefully)
    - Antimeridian-crossing geometries (basic support)
    """
    def try_float(val: Any) -> Optional[float]:
        """Safely convert a value to float."""
        try:
            return float(val)
        except (TypeError, ValueError):
            return None
    
    def iter_coords(node: Any):
        """Recursively iterate through nested coordinate arrays."""
        if node is None:
            return
        if isinstance(node, (list, tuple)):
            # Check if this looks like a coordinate (2-4 numeric values)
            if len(node) >= 2 and len(node) <= 4:
                first_val = try_float(node[0])
                second_val = try_float(node[1])
                if first_val is not None and second_val is not None:
                    yield (first_val, second_val)
                    return
            # It's a nested array, recurse
            for item in node:
                yield from iter_coords(item)

    def extract_coords_from_geometry(geom: Optional[dict]) -> list:
        """Extract all coordinates from a geometry object."""
        if not geom or not isinstance(geom, dict):
            return []
        
        geom_type = geom.get("type")
        
        # Handle GeometryCollection specially (has 'geometries' not 'coordinates')
        if geom_type == "GeometryCollection":
            all_coords = []
            for sub_geom in geom.get("geometries") or []:
                all_coords.extend(extract_coords_from_geometry(sub_geom))
            return all_coords
        
        # Standard geometry with coordinates
        coords = geom.get("coordinates")
        if coords:
            return list(iter_coords(coords))
        return []

    def extract_all_coords(obj: dict) -> list:
        """Extract coordinates from any GeoJSON structure."""
        if not isinstance(obj, dict):
            return []
            
        geom_type = obj.get("type")
        
        if geom_type == "FeatureCollection":
            all_coords = []
            for feat in obj.get("features") or []:
                if isinstance(feat, dict):
                    geom = feat.get("geometry")
                    all_coords.extend(extract_coords_from_geometry(geom))
            return all_coords
            
        elif geom_type == "Feature":
            return extract_coords_from_geometry(obj.get("geometry"))
            
        else:
            # Assume it's a geometry object
            return extract_coords_from_geometry(obj)

    try:
        coords = extract_all_coords(obj)
        
        if not coords:
            print(f"  WARNING: No valid coordinates found in GeoJSON (type: {obj.get('type')})")
            return None
        
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]
        
        # Basic validation
        if not xs or not ys:
            print(f"  WARNING: Empty coordinate arrays after extraction")
            return None
        
        bbox = [min(xs), min(ys), max(xs), max(ys)]
        
        # Sanity check: valid coordinate ranges
        if bbox[0] < -180 or bbox[2] > 180 or bbox[1] < -90 or bbox[3] > 90:
            print(f"  WARNING: Bbox has unusual coordinates (possibly swapped lat/lon?): {bbox}")
            # Try swapping if it looks like lat/lon are reversed
            if -90 <= bbox[0] <= 90 and -90 <= bbox[2] <= 90:
                print(f"  Attempting to swap lat/lon...")
                xs, ys = ys, xs
                bbox = [min(xs), min(ys), max(xs), max(ys)]
        
        print(f"  Extracted bbox: {bbox}")
        return bbox
        
    except Exception as e:
        print(f"  ERROR extracting bbox: {e}")
        return None


def _stac_search(
    *, 
    bbox: list[float], 
    collection: str, 
    max_items: int, 
    cloud_cover_lte: Optional[float],
    next_token: Optional[str] = None
) -> dict[str, Any]:
    """Search STAC catalog with pagination support."""
    url = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
    body: dict[str, Any] = {
        "collections": [collection],
        "bbox": bbox,
        "limit": min(max_items, 100),  # API typically limits to 100 per page
    }
    if cloud_cover_lte is not None:
        body["query"] = {"eo:cloud_cover": {"lte": cloud_cover_lte}}
    if next_token:
        body["token"] = next_token

    resp = requests.post(url, json=body, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _calculate_scenes_coverage(
    scenes_footprints: list[dict[str, Any]], 
    boundary_geojson: dict[str, Any]
) -> tuple[float, Any]:
    """
    Calculate the combined coverage of scenes over the boundary.
    
    Returns:
        Tuple of (coverage_percent, covered_geometry)
    """
    from shapely.geometry import shape
    from shapely.ops import unary_union
    from backend.utils.coverage_validator import extract_boundary_geometry
    
    if not scenes_footprints:
        return 0.0, None
    
    boundary_geom = extract_boundary_geometry(boundary_geojson)
    boundary_area = boundary_geom.area
    
    if boundary_area == 0:
        return 0.0, None
    
    # Convert all footprints to shapely geometries
    footprint_geoms = []
    for fp in scenes_footprints:
        try:
            geom = extract_boundary_geometry(fp)
            if boundary_geom.intersects(geom):
                footprint_geoms.append(geom)
        except Exception:
            continue
    
    if not footprint_geoms:
        return 0.0, None
    
    # Union all footprints and intersect with boundary
    combined = unary_union(footprint_geoms)
    covered = boundary_geom.intersection(combined)
    coverage_percent = (covered.area / boundary_area) * 100.0
    
    return coverage_percent, covered


@app.post("/jobs/ingest-stac", response_model=list[ImagerySceneOut])
def ingest_stac_job(payload: StacIngestJobCreate) -> list[ImagerySceneOut]:
    """
    Ingest satellite imagery scenes from STAC catalog.
    
    With ensure_coverage=True (default), this will keep fetching scenes until
    the mine boundary is fully covered or max_items is reached.
    """
    conn = get_db()
    try:
        mine = conn.execute("SELECT boundary_geojson FROM mine_area WHERE id = 1").fetchone()
        if mine is None:
            raise HTTPException(status_code=400, detail="Mine area not configured")

        boundary = json.loads(mine["boundary_geojson"])
        bbox = _bbox_from_geojson(boundary)
        if bbox is None:
            raise HTTPException(status_code=400, detail="Unable to derive bbox from boundary GeoJSON")

        now = _utc_now_iso()
        created: list[ImagerySceneOut] = []
        all_footprints: list[dict[str, Any]] = []
        total_fetched = 0
        next_token = None
        coverage_achieved = False
        
        print(f"\n{'='*60}")
        print(f"STAC INGESTION - Coverage-Aware Mode")
        print(f"{'='*60}")
        print(f"Target coverage: {payload.min_coverage_percent}%")
        print(f"Max items: {payload.max_items}")
        
        # Fetch scenes in batches until coverage is achieved or limit reached
        while total_fetched < payload.max_items and not coverage_achieved:
            batch_size = min(50, payload.max_items - total_fetched)
            
            search = _stac_search(
                bbox=bbox,
                collection=payload.collection,
                max_items=batch_size,
                cloud_cover_lte=payload.cloud_cover_lte,
                next_token=next_token,
            )

            features = search.get("features") or []
            if not features:
                print(f"  No more scenes available from STAC catalog")
                break
            
            # Get next page token if available
            links = search.get("links") or []
            next_token = None
            for link in links:
                if link.get("rel") == "next":
                    # Extract token from href or use the token field
                    next_token = link.get("body", {}).get("token")
                    break
            
            print(f"\nBatch: Fetched {len(features)} scenes...")
            
            for item in features:
                props = item.get("properties") or {}
                acquired_at = props.get("datetime") or props.get("start_datetime") or now
                cloud = props.get("eo:cloud_cover")
                uri = item.get("id")
                footprint = item.get("geometry")

                # Check if scene already exists to avoid duplicates
                existing = conn.execute("SELECT id FROM imagery_scene WHERE uri = ?", (str(uri),)).fetchone()
                if existing:
                    # Still count footprint for coverage calculation
                    if footprint:
                        all_footprints.append(footprint)
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
                
                if footprint:
                    all_footprints.append(footprint)
                    
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
            
            total_fetched += len(features)
            
            # Check coverage if ensure_coverage is enabled
            if payload.ensure_coverage and all_footprints:
                coverage_percent, _ = _calculate_scenes_coverage(all_footprints, boundary)
                print(f"  Current coverage: {coverage_percent:.1f}%")
                
                if coverage_percent >= payload.min_coverage_percent:
                    coverage_achieved = True
                    print(f"  ✓ Target coverage achieved!")
            
            # If no next page token, we've exhausted the catalog
            if not next_token:
                print(f"  Reached end of STAC catalog results")
                break
        
        # Final coverage report
        if all_footprints:
            final_coverage, _ = _calculate_scenes_coverage(all_footprints, boundary)
            print(f"\n{'='*60}")
            print(f"INGESTION COMPLETE")
            print(f"  Total scenes ingested: {len(created)}")
            print(f"  Final boundary coverage: {final_coverage:.1f}%")
            if final_coverage < payload.min_coverage_percent:
                print(f"  ⚠️ WARNING: Coverage below target ({payload.min_coverage_percent}%)")
                print(f"     Some parts of the boundary may not have imagery")
            print(f"{'='*60}\n")

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


@app.get("/imagery/latest/preview")
def get_latest_imagery_preview() -> dict[str, Any]:
    """
    Returns an RGB preview for the latest imagery scene.
    Generates the preview from downloaded bands if not already cached.
    This endpoint works independently of analysis runs.
    """
    conn = get_db()
    try:
        row = conn.execute(
            """
            SELECT uri, footprint_geojson
            FROM imagery_scene
            WHERE uri IS NOT NULL
            ORDER BY acquired_at DESC
            LIMIT 1
            """
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="No imagery scenes available")

        uri = row["uri"]
        base_dir = Path(__file__).parent / "data" / "imagery"
        
        # Check for RGB bands (B04=Red, B03=Green, B02=Blue)
        red = base_dir / f"{uri}_B04.tif"
        green = base_dir / f"{uri}_B03.tif"
        blue = base_dir / f"{uri}_B02.tif"

        if not (red.exists() and green.exists() and blue.exists()):
            # Bands not downloaded yet - return null preview with helpful message
            return {
                "preview": None,
                "message": "RGB bands not yet downloaded. Run an analysis or STAC ingest to download imagery.",
                "bands_available": {
                    "B02": blue.exists(),
                    "B03": green.exists(),
                    "B04": red.exists()
                }
            }

        # Generate RGB preview
        preview_data = generate_rgb_png(
            str(red), str(green), str(blue), 
            f"latest_preview_{uri}",
            brightness=2.5
        )

        return {
            "preview": preview_data,
            "uri": uri,
            "footprint": json.loads(row["footprint_geojson"]) if row["footprint_geojson"] else None
        }
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


@app.get("/analysis-runs/latest/stats")
def get_latest_analysis_stats() -> dict[str, Any]:
    """Get statistics from the most recent analysis run"""
    conn = get_db()
    try:
        # Get latest run
        run = conn.execute(
            "SELECT id, created_at, baseline_date, latest_date FROM analysis_run ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        
        if not run:
            return {
                "has_data": False,
                "vegetation_loss_ha": 0,
                "vegetation_gain_ha": 0,
                "mining_expansion_ha": 0,
                "water_accumulation_ha": 0,
                "total_change_ha": 0,
                "last_updated": None,
            }
        
        run_id = run["id"]
        
        # Get zone totals
        zones = conn.execute(
            """
            SELECT zone_type, SUM(area_ha) as total_area
            FROM analysis_zone
            WHERE run_id = ?
            GROUP BY zone_type
            """,
            (run_id,)
        ).fetchall()
        
        stats = {
            "vegetation_loss": 0.0,
            "vegetation_gain": 0.0,
            "mining_expansion": 0.0,
            "water_accumulation": 0.0,
        }
        
        for zone in zones:
            zone_type = zone["zone_type"]
            if zone_type in stats:
                stats[zone_type] = float(zone["total_area"])
        
        total_change = sum(stats.values())
        
        return {
            "has_data": True,
            "vegetation_loss_ha": stats["vegetation_loss"],
            "vegetation_gain_ha": stats["vegetation_gain"],
            "mining_expansion_ha": stats["mining_expansion"],
            "water_accumulation_ha": stats["water_accumulation"],
            "total_change_ha": total_change,
            "last_updated": run["created_at"],
            "baseline_date": run["baseline_date"],
            "latest_date": run["latest_date"],
        }
    finally:
        conn.close()


@app.get("/alerts", response_model=list[AlertOut])
def list_alerts(limit: int = 50) -> list[AlertOut]:
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT id, run_id, alert_type, title, description, location, severity, geometry_geojson, created_at
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
                geometry=json.loads(r["geometry_geojson"]) if r["geometry_geojson"] else None,
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


@app.delete("/analysis-runs/clear-all")
def clear_all_analysis() -> dict[str, str]:
    """Delete all analysis runs, zones, alerts, AND imagery"""
    conn = get_db()
    try:
        # 1. Delete database records in correct order
        conn.execute("DELETE FROM alert")
        conn.execute("DELETE FROM analysis_zone")
        conn.execute("DELETE FROM analysis_run")
        conn.execute("DELETE FROM imagery_scene")
        conn.commit()

        # 2. Delete physical files (Imagery Bands)
        # Defined in backend/utils/stac_downloader.py
        imagery_dir = Path(__file__).parent / "data" / "imagery"
        if imagery_dir.exists():
            for file in imagery_dir.glob("*"):
                if file.is_file():
                    try:
                        file.unlink()
                    except Exception as e:
                        print(f"Failed to delete {file}: {e}")

        # 3. Delete physical files (Cache/Previews)
        if CACHE_DIR.exists():
            for file in CACHE_DIR.glob("*"):
                if file.is_file():
                    try:
                        file.unlink()
                    except Exception as e:
                        print(f"Failed to delete {file}: {e}")

        return {"status": "success", "message": "All analysis data and imagery cleared"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clear data: {str(e)}")
    finally:
        conn.close()


@app.get("/analysis-runs/{run_id}/indices")
def get_run_indices(run_id: int) -> dict[str, Any]:
    """
    Returns URLs and metadata for all index layers (NDVI, NDWI, BSI) for an analysis run.
    Includes baseline, latest, and change detection layers.
    """
    from pathlib import Path as PathLib
    
    cache_dir = CACHE_DIR
    index_dir = PathLib(__file__).parent / "data" / "indices"
    
    def get_layer_info(prefix: str, index_type: str) -> Optional[dict[str, Any]]:
        """Get preview URL and bounds for an index layer if it exists."""
        preview_name = f"run{run_id}_{prefix}_{index_type}.png"
        preview_path = cache_dir / preview_name
        geotiff_name = f"run{run_id}_{prefix}_{index_type}.tif"
        geotiff_path = index_dir / geotiff_name
        
        if preview_path.exists():
            bounds = None
            if geotiff_path.exists():
                try:
                    from backend.utils.spatial import get_raster_bounds_4326
                    bounds = get_raster_bounds_4326(str(geotiff_path))
                except Exception:
                    pass
            
            return {
                "url": f"/data/cache/{preview_name}",
                "bounds": bounds,
                "geotiff_url": f"/data/indices/{geotiff_name}" if geotiff_path.exists() else None
            }
        return None
    
    def get_change_layer_info(index_type: str) -> Optional[dict[str, Any]]:
        """Get preview URL and bounds for a change detection layer."""
        preview_name = f"run{run_id}_change_{index_type}.png"
        preview_path = cache_dir / preview_name
        geotiff_name = f"run{run_id}_change_{index_type}.tif"
        geotiff_path = index_dir / geotiff_name
        
        if preview_path.exists():
            bounds = None
            if geotiff_path.exists():
                try:
                    from backend.utils.spatial import get_raster_bounds_4326
                    bounds = get_raster_bounds_4326(str(geotiff_path))
                except Exception:
                    pass
            
            return {
                "url": f"/data/cache/{preview_name}",
                "bounds": bounds,
                "geotiff_url": f"/data/indices/{geotiff_name}" if geotiff_path.exists() else None
            }
        return None
    
    return {
        "run_id": run_id,
        "baseline": {
            "ndvi": get_layer_info("baseline", "ndvi"),
            "ndwi": get_layer_info("baseline", "ndwi"),
            "bsi": get_layer_info("baseline", "bsi"),
        },
        "latest": {
            "ndvi": get_layer_info("latest", "ndvi"),
            "ndwi": get_layer_info("latest", "ndwi"),
            "bsi": get_layer_info("latest", "bsi"),
        },
        "change": {
            "ndvi": get_change_layer_info("ndvi"),
            "ndwi": get_change_layer_info("ndwi"),
            "bsi": get_change_layer_info("bsi"),
        }
    }


# Mount indices directory for serving GeoTIFFs
INDEX_DIR = Path(__file__).parent / "data" / "indices"
INDEX_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/data/indices", StaticFiles(directory=INDEX_DIR), name="indices")


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
