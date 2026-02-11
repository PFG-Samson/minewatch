# MineWatch

MineWatch is a web application that helps teams monitor land-use and environmental changes around mining sites using satellite imagery and GIS.

**Key Features:**

- **Real Scientific Analysis Pipeline:** Authentic calculation of **NDVI** (Vegetation), **BSI** (Bare Soil), and **NDWI** (Water) from multi-spectral Sentinel-2 satellite imagery with change detection between acquisition dates.
- **Intelligent Alert System:** Configurable rule-based alerts with severity levels (high/medium/low) based on area thresholds and change types.
- **Scene Selection Controls:** Users can select specific baseline and latest scenes for analysis via UI dropdowns showing acquisition dates and cloud cover.
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
3. Paste or upload your boundary GeoJSON (WGS84), set your buffer distance, enter site name/description, and click **Save Configuration**.
4. Navigate to **Satellite Imagery** tab and click **Sync STAC** to search and register available Sentinel-2 scenes (metadata only).
5. Select a **Baseline** and **Latest** scene, then click **Run Selected Analysis** to trigger change detection.
   - *Alternatively*, the dashboard **auto-runs analysis on mount** using the 2 most recent scenes if available.
6. View results on the **Dashboard** (stats cards), **Map** (color-coded zones), or **Alerts** tab.
7. Click **"View on Map"** on any alert to see its exact location highlighted on the map.
8. Click **Generate Report** to download a PDF summary of the analysis.

## Key API endpoints

- `GET /health`
- `GET /mine-area`, `PUT /mine-area`
- `POST /jobs/ingest-stac` - Search STAC catalog and register scene metadata (does NOT download imagery)
- `GET /imagery`, `GET /imagery/latest`, `POST /imagery`
- `POST /analysis-runs` - Downloads imagery bands, runs analysis, generates zones and alerts
- `GET /analysis-runs/{run_id}`, `GET /analysis-runs/{run_id}/report`
- `GET /alerts` - Returns alerts with geometry for map visualization
- `GET /alert-rules`, `PUT /alert-rules` - Manage alert rule configuration

## STAC Ingestion Workflow

The STAC ingestion queries Microsoft Planetary Computer STAC API:

**What it does:**
- Searches for Sentinel-2 L2A scenes within your mine boundary bounding box
- Filters by cloud cover (≤20% by default)
- Registers scene **metadata only** in the database:
  - Scene ID (URI)
  - Acquisition date/time
  - Cloud cover percentage
  - Footprint geometry (GeoJSON)

**What it does NOT do:**
- Does NOT download actual imagery files (.tif bands)
- Imagery is downloaded later during analysis runs

**Buttons:**
- **"Ingest via STAC"** (Dashboard): Fetches up to 10 scenes
- **"Sync STAC"** (Imagery tab): Fetches up to 20 scenes
- **"Start First Ingestion"** (Imagery tab empty state): Fetches up to 20 scenes

## Analysis Workflow

The system performs real change detection comparing two satellite scenes:

**Automatic Trigger:**
- Dashboard automatically runs analysis on mount using 2 most recent scenes

**Manual Trigger:**
1. User selects baseline and latest scenes
2. Clicks "Run Analysis" button in Imagery or Analysis tab

**Processing Steps:**
1. **Download Bands** - Fetches required bands from Planetary Computer:
   - B02 (Blue), B03 (Green), B04 (Red), B08 (NIR), B11 (SWIR)
   - Saves to `backend/data/imagery/` as `.tif` files
   - Caches locally (skips re-downloading existing files)

2. **Clip to AOI** - Clips rasters to mine boundary + buffer zone

3. **Calculate Indices**:
   - **NDVI** (Vegetation): `(NIR - Red) / (NIR + Red)`
   - **BSI** (Bare Soil): BSI calculation from Red, Blue, NIR, SWIR
   - **NDWI** (Water): `(Green - NIR) / (Green + NIR)`

4. **Detect Changes**:
   - Vegetation loss: NDVI drop > 0.15
   - Soil exposure: BSI increase > 0.1
   - Water accumulation: NDWI increase > 0.2

5. **Vectorize** - Converts change masks into GeoJSON polygon features

6. **Generate Alerts** - Creates alerts with geometry using configurable rules

7. **Save Results** - Stores zones, alerts (with geometry), and metadata in database

**Note:** If only one scene is available, the system returns empty results. Run STAC ingestion to get at least 2 scenes from different dates.

## Alert Rules Configuration

The system uses a configurable rule-based alert engine defined in `backend/config/alert_rules.json`:

**Alert Types:**
- **Vegetation Loss**: High (>1.0 ha), Medium (>0.5 ha), Low (>0.2 ha)
- **Mining Expansion**: Medium (>0.1 ha), Low (>0.05 ha) 
- **Water Accumulation**: Low (>0.05 ha)
- **Boundary Breach**: High (any activity outside approved boundary)

**API Endpoints:**
- `GET /alert-rules` - Get current configuration
- `PUT /alert-rules` - Update thresholds (admin only)

**Customization:**
Edit `backend/config/alert_rules.json` to adjust thresholds, enable/disable rules, or modify alert messages.

## Troubleshooting (Windows)

- If `pip.exe` access is denied, use `python -m pip ...` in a **user-writable** environment.
- If your Anaconda `base` env is read-only, create a local env inside the repo (example):

```sh
conda create -p .\.minewatch-env python=3.11 -y
conda activate .\.minewatch-env
python -m pip install -r backend/requirements.txt
```