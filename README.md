# MineWatch

MineWatch is a web application that helps teams monitor land-use and environmental changes around mining sites using satellite imagery and GIS.

Current capabilities:

- **Mine boundary setup** (upload/paste GeoJSON)
- **Satellite metadata ingestion via STAC** (Sentinel‑2 L2A using Microsoft Planetary Computer)
- **Analysis runs** (currently generates demo change zones/alerts; pipeline is structured to become NDVI-based next)
- **Interactive map** (renders boundary, buffer, zones; auto-zooms to your saved boundary)
- **Alerts + PDF report generation**

## Repository structure

- `backend/` FastAPI + SQLite API
- `src/` React + Vite frontend

## Prerequisites

- Node.js 18+
- Python 3.10+ recommended (Windows: use a project-local venv/conda env that is writable)

## Run the backend (FastAPI)

1) Create/activate an environment

2) Install backend deps:

```sh
python -m pip install -r backend/requirements.txt
```

3) Start the API:

```sh
python -m uvicorn backend.main:app --reload --port 8000
```

Health check:

- `GET http://127.0.0.1:8000/health`

## Run the frontend (React)

```sh
npm install
npm run dev
```

Frontend:

- `http://localhost:8080/dashboard`

## How to use (happy path)

1) Open the Dashboard.
2) In **Mine Area Setup**, paste or upload your boundary GeoJSON and click **Save**.
3) In **Satellite Source**, click **Ingest via STAC**.
4) Click **Refresh** to create an analysis run.
5) Click **Generate Report** to download a PDF for the current run.

## Key API endpoints

- `GET /health`
- `GET /mine-area`, `PUT /mine-area`
- `POST /jobs/ingest-stac` (STAC search + store scenes as `imagery_scene` rows)
- `GET /imagery`, `GET /imagery/latest`, `POST /imagery`
- `POST /analysis-runs`, `GET /analysis-runs/{run_id}`, `GET /analysis-runs/{run_id}/report`
- `GET /alerts`

## STAC ingestion notes

The STAC ingestion job queries the Planetary Computer STAC API:

- `https://planetarycomputer.microsoft.com/api/stac/v1/search`

It uses your saved mine boundary to derive a bounding box and searches Sentinel‑2 L2A items, storing:

- acquisition datetime
- cloud cover (when available)
- scene footprint geometry
- scene identifier

## Troubleshooting (Windows)

- If `pip.exe` access is denied, use `python -m pip ...` in a **user-writable** environment.
- If your Anaconda `base` env is read-only, create a local env inside the repo (example):

```sh
conda create -p .\.minewatch-env python=3.11 -y
conda activate .\.minewatch-env
python -m pip install -r backend/requirements.txt
```