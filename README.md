# MineWatch

MineWatch is a web application that helps teams monitor land-use and environmental changes around mining sites using satellite imagery and GIS.

**Key Features:**

- **Real Scientific Analysis Pipeline:** Authentic calculation of **NDVI** (Vegetation), **BSI** (Bare Soil), and **NDWI** (Water) from multi-spectral Sentinel-2 satellite imagery with change detection between acquisition dates.
- **Dedicated Settings Tab:** Full-screen project configuration for Site Name, Description, GeoJSON boundary upload, and Buffer zone.
- **Automated Satellite Ingestion via STAC:** Metadata search and automated band download (B02-Blue, B03-Green, B04-Red, B08-NIR, B11-SWIR) from Microsoft Planetary Computer.
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

## NDVI Analysis

The system performs real change detection by comparing satellite imagery from two different acquisition dates:

1. Downloads required bands (B02, B03, B04, B08, B11) for baseline and latest scenes
2. Clips imagery to mine boundary + buffer zone  
3. Computes vegetation (NDVI), bare soil (BSI), and water (NDWI) indices
4. Detects significant changes (vegetation loss > 0.15, soil exposure > 0.1, water accumulation > 0.2)
5. Vectorizes change masks into GeoJSON polygons stored as analysis zones
6. Generates alerts for significant changes (> 0.5 hectares)

**Note:** If only one scene is available, the system will return empty results with a warning. Run STAC ingestion to download at least 2 scenes from different dates for meaningful change detection.

## Troubleshooting (Windows)

- If `pip.exe` access is denied, use `python -m pip ...` in a **user-writable** environment.
- If your Anaconda `base` env is read-only, create a local env inside the repo (example):

```sh
conda create -p .\.minewatch-env python=3.11 -y
conda activate .\.minewatch-env
python -m pip install -r backend/requirements.txt
```