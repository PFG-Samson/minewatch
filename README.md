# MineWatch

MineWatch is a web application that helps teams monitor land-use and environmental changes around mining sites using satellite imagery and GIS.

**Key Features:**

- **Real Scientific Analysis Pipeline:** Authentic calculation of **NDVI** (Vegetation), **BSI** (Bare Soil), and **NDWI** (Water) from multi-spectral Sentinel-2 satellite imagery with change detection between acquisition dates.
- **Production-Grade Multi-Scene Mosaicking:** Automatically combines multiple satellite tiles when a single scene doesn't fully cover the AOI, with intelligent scene selection based on cloud cover and acquisition date.
- **Comprehensive Coverage Validation:** Validates imagery coverage at every step (pre-download, post-download, post-mosaic) ensuring minimum 95% boundary coverage or graceful failure with actionable guidance.
- **Intelligent Scene Selection:** Prioritizes low-cloud scenes within 30 days of target date, filters out scenes with >80% cloud cover, and dynamically calculates required scenes based on AOI size.
- **Intelligent Alert System:** Configurable rule-based alerts with severity levels (high/medium/low) based on area thresholds and change types.
- **Scene Selection Controls:** Users can select specific baseline and latest scenes for analysis via UI dropdowns showing acquisition dates and cloud cover.
- **Dedicated Settings Tab:** Full-screen project configuration for Site Name, Description, GeoJSON boundary upload, and Buffer zone.
- **Automated Satellite Ingestion via STAC:** Metadata search and automated band download (B02-Blue, B03-Green, B04-Red, B08-NIR, B11-SWIR) from Microsoft Planetary Computer with coverage-aware ingestion.
- **Interactive Map:** Renders boundaries, buffer zones, and scientific change overlays; features reactive zoom to latest AOI.
- **Alerts + PDF Reports:** Automated detection of significant land changes with PDF summary export.
- **Production-Ready Error Handling:** Graceful failures with detailed error messages, run status tracking, and user-actionable guidance.

## Repository structure

- `backend/` FastAPI + SQLite API + Scientific Utilities + Production Configuration
- `src/` React + Vite frontend
- `FAQ.md` Comprehensive project Q&A
- `PRODUCTION_READY_SUMMARY.md` Production deployment guide
- `COVERAGE_ANALYSIS.md` Technical coverage analysis

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

**Multi-Scene Mosaicking:**
- If a single scene doesn't fully cover the AOI (< 92% coverage), the system automatically:
  1. Searches for additional scenes from the database
  2. Prioritizes scenes with low cloud cover and similar acquisition dates
  3. Downloads and mosaics multiple tiles to achieve 95%+ coverage
  4. Validates final coverage before proceeding

**Coverage Validation:**
- Pre-download: Checks scene footprints from STAC metadata
- Post-download: Validates actual pixel data coverage
- Post-mosaic: Ensures combined coverage meets requirements
- Graceful Failure: If coverage < 95%, analysis fails with:
  - Current coverage percentage
  - Number of scenes attempted
  - Actionable guidance (e.g., "Run STAC ingestion for more scenes")

**Note:** If only one scene is available and it doesn't meet minimum coverage, the system will fail with guidance. Run STAC ingestion to get more scenes. At least 2 different scenes are required for change detection.

## Configuration

### Alert Rules Configuration

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

### Coverage & Validation Configuration

Production-grade configuration in `backend/config.py`:

**Coverage Thresholds:**
```python
COVERAGE_CONFIG = {
    "MINIMUM_REQUIRED": 95.0,      # Hard requirement for analysis
    "MOSAIC_THRESHOLD": 92.0,      # Triggers multi-scene mosaicking
    "TARGET_COVERAGE": 98.0,       # Ideal goal
    "DOWNLOAD_MINIMUM": 80.0       # Per-scene minimum
}
```

**Temporal Configuration:**
```python
TEMPORAL_CONFIG = {
    "MAX_DATE_DIFF_DAYS": 30.0,    # Max days between scenes in mosaic
}
```

**Scene Selection:**
```python
SCENE_CONFIG = {
    "MAX_CLOUD_COVER": 80.0,       # Skip scenes above this
    "PREFER_LOW_CLOUD": True,      # Prioritize clearer scenes
}
```

**Validation Flags:**
```python
VALIDATION_CONFIG = {
    "REQUIRE_DB_CONN": True,       # Required in production
    "VALIDATE_POST_MOSAIC": True,  # Validate after mosaicking
    "FAIL_ON_INSUFFICIENT_COVERAGE": True  # Strict validation
}
```

**Adjusting for Your Use Case:**
- For larger AOIs where 95% is too strict: Lower `MINIMUM_REQUIRED` to 90%
- For rapid monitoring: Set `MAX_DATE_DIFF_DAYS` to 7 days
- For development/testing: Set `REQUIRE_DB_CONN` and `FAIL_ON_INSUFFICIENT_COVERAGE` to False

See `PRODUCTION_READY_SUMMARY.md` for complete configuration guide.

## Troubleshooting (Windows)

- If `pip.exe` access is denied, use `python -m pip ...` in a **user-writable** environment.
- If your Anaconda `base` env is read-only, create a local env inside the repo (example):

```sh
conda create -p .\.minewatch-env python=3.11 -y
conda activate .\.minewatch-env
python -m pip install -r backend/requirements.txt
```