# MineWatch

MineWatch is a web application that helps teams monitor land-use and environmental changes around mining sites using satellite imagery and GIS.

Current capabilities:

- **Scientific Analysis Pipeline:** Real-time calculation of **NDVI** (Vegetation), **BSI** (Bare Soil), and **NDWI** (Water) from multi-spectral Sentinel-2 bands.
- **Dedicated Settings Tab:** Full-screen project configuration for Site Name, Description, GeoJSON boundary upload, and Buffer zone.
- **Satellite Ingestion via STAC:** Metadata search and automated band download (Red, Green, Blue, NIR, SWIR1) from Microsoft Planetary Computer.
- **Interactive Map:** Renders boundaries, buffer zones, and scientific change overlays; features reactive zoom to latest AOI.
- **Alerts + PDF Reports:** Automated detection of significant land changes with PDF summary export.

## Repository structure

- `backend/` FastAPI + SQLite API + Scientific Utilities
- `src/` React + Vite frontend
- `FAQ.md` Comprehensive project Q&A

## Prerequisites

- Node.js 18+
- Python 3.10+ recommended (with `rasterio`, `numpy`, `shapely`, `pystac`)

## Run the App

1. **Start the Backend (Terminal 1):**
   ```sh
   python -m pip install -r backend/requirements.txt
   python -m backend.main
   ```

2. **Start the Frontend (Terminal 2):**
   ```sh
   npm install
   npm run dev
   ```

## How to use (happy path)

1. Open the [Dashboard](http://localhost:8080/dashboard).
2. Go to the **Settings** tab.
3. Paste or upload your boundary GeoJSON, set your buffer, and click **Save Configuration**.
4. In the **Satellite Imagery** tab, click **Run STAC Ingest Job** to find latest scenes.
5. In **Change Analysis**, click **Run New Analysis** to compare indices between dates.
6. Check **Alerts** and click **Generate Report** to download the findings.

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