# MineWatch — Task Log

## Why this file exists
This file is a lightweight “pause/resume” log for the MineWatch project.

It answers:

- what we have already built
- where we stopped
- what is next (in priority order)

---

## Current state (as of today)

### Working end-to-end flow
- You can run the **frontend** (React/Vite) and **backend** (FastAPI/SQLite).
- You can **save a mine boundary GeoJSON** (Mine Area Setup).
- The map **renders the saved boundary**, draws a **buffer**, and **auto-zooms** to the saved boundary.
- You can ingest real satellite *metadata* using STAC:
  - Backend endpoint: `POST /jobs/ingest-stac`
  - Source: **Microsoft Planetary Computer STAC**
  - Collection: **Sentinel‑2 L2A**
  - Stored in DB table: `imagery_scene`
- You can create analysis runs and download a PDF report.

### What is real vs placeholder
- **Real:** Mine boundary storage, STAC ingestion (metadata), imagery list/latest endpoints, analysis run persistence, PDF generation, map rendering.
- **Placeholder:** Change-detection results (zones/alerts) are still demo outputs in `backend/analysis_pipeline.py`.

---

## What we completed

### Backend
- FastAPI service with SQLite persistence:
  - mine boundary + buffer
  - imagery scenes (`imagery_scene`)
  - analysis runs + zones + alerts
- STAC ingestion endpoint:
  - `POST /jobs/ingest-stac`
- Removed dummy ingestion/seed endpoints:
  - removed `/jobs/ingest`
  - removed `/imagery/seed`

### Frontend
- Dashboard wired to backend using React Query.
- STAC-only ingest button:
  - “Ingest via STAC”
- “Active Alerts” stat uses real alert count.

### Map
- Shows mine boundary and buffer.
- Draws an extent rectangle (bounds) around the boundary.
- Auto-zooms to the saved boundary.

---

## Where we stopped

We stopped right after:

- confirming STAC ingestion works (it returns real Sentinel‑2 items and stores them)
- removing dummy ingestion/seeding
- updating map zoom/extent behavior
- updating `README.md`

---

## What’s next (priority order)

### P0 — Implement real NDVI change detection
Goal: produce real change polygons/rasters instead of demo polygons.

Suggested incremental plan:

1) **Download/stream required Sentinel‑2 assets** from the STAC items (B04 + B08 bands at 10m) and clip to the mine boundary + buffer.
2) Compute NDVI for baseline and latest:
   - `ndvi = (nir - red) / (nir + red)`
3) Compute NDVI delta and classify:
   - vegetation loss
   - vegetation gain
   - no change
4) Convert change mask(s) into polygons (vectorize) and store as `analysis_zone` GeoJSON.

Notes:
- This will likely require adding optional deps:
  - `numpy`, `rasterio`, `shapely`, `pyproj`, `pystac-client` (or keep stdlib HTTP + rasterio)
- The current app structure already supports replacing the pipeline without changing the UI/API.

### P0 — Choose how to handle imagery storage
Decide whether to:

- store downloaded bands in local disk under `backend/data/` (simple)
- or store in cloud object storage later

### P1 — Better analysis run controls
- allow user to explicitly pick baseline/latest scenes in UI
- show scene list and dates

### P1 — Alerts rules
Replace demo alerts with rules based on computed zones:

- vegetation loss area > X ha
- change detected outside boundary

### P2 — Map layers for imagery
- show baseline and latest imagery tiles (initially as simple links or static overlays)
- later: tile server / COG tiling

---

## How to resume quickly

1) Start backend:

```sh
python -m uvicorn backend.main:app --reload --port 8000
```

2) Start frontend:

```sh
npm run dev
```

3) In the dashboard:

- Save mine boundary
- Ingest via STAC
- Refresh analysis
- Download report
