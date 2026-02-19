# MineWatch Backend

FastAPI server providing production-grade satellite imagery analysis, intelligent multi-scene mosaicking, comprehensive coverage validation, STAC integration, and alert generation.

## Quick Start

1. Create a virtualenv and install deps:

```bash
pip install -r requirements.txt
```

2. Start the API:

```bash
python -m backend.main
# Or: uvicorn backend.main:app --reload --port 8000
```

Health check: http://localhost:8000/health

## Architecture

- **FastAPI** - Web framework with OpenAPI docs at `/docs`
- **SQLite** - Local database (`backend/data/minewatch.db`)
- **Rasterio + NumPy** - Geospatial raster processing
- **Shapely + PyProj** - Vector geometry operations
- **pystac + requests** - STAC catalog integration
- **Production Configuration** - Centralized config system (`backend/config.py`)
- **Custom Exceptions** - Rich error context (`backend/exceptions.py`)

## Key Endpoints

### Configuration
- `GET /mine-area` - Get mine boundary configuration
- `PUT /mine-area` - Update mine boundary and settings

### Satellite Imagery (STAC)
- `POST /jobs/ingest-stac` - Search STAC catalog, register metadata
- `GET /imagery` - List all registered scenes
- `GET /imagery/latest` - Get most recent scene

### Analysis
- `POST /analysis-runs` - Create new analysis (auto-downloads imagery, mosaics if needed, runs processing)
  - **Returns HTTP 422** if coverage insufficient (< 95%)
  - **Returns HTTP 400** if identical scenes selected
  - **Returns HTTP 500** if mosaic fails
- `GET /analysis-runs` - List all runs
- `GET /analysis-runs/{id}` - Get specific run with zones (GeoJSON)
- `GET /analysis-runs/latest/stats` - Get aggregated statistics
- `GET /analysis-runs/{id}/report` - Download PDF report
- `GET /analysis-runs/{id}/imagery` - Get RGB preview URLs and bounds
- `GET /analysis-runs/{id}/indices` - Get index layer URLs (NDVI, NDWI, BSI)

### PDF Report Generator
- Deterministic ReportLab-based generator with strict section order
- Real AOI metrics (geodesic area/perimeter, centroid, bounding box, buffer)
- Coverage quality: precise footprint intersection; approximate index bounds fallback
- Scene details parsed from URI (Platform, Level, Tile)
- Labeled imagery (Baseline/Latest) and index previews (Baseline/Latest/Change) with legends
- Index statistics (baseline/latest means, delta) and structured tables (Zones, Alerts)
- Reliability improvements: Content-Length header; preview downsampling to avoid large-image warnings

### Alerts
- `GET /alerts` - List alerts with geometry
- `GET /alert-rules` - Get alert rule configuration
- `PUT /alert-rules` - Update alert thresholds

## Data Flow

1. **STAC Ingestion** (`/jobs/ingest-stac`)
   - Queries Microsoft Planetary Computer
   - Filters by cloud cover (≤ 80% by default)
   - Saves scene metadata + footprint to `imagery_scene` table
   - **Coverage-Aware:** Continues fetching until boundary is covered (if `ensure_coverage=true`)
   - Does NOT download imagery files (metadata only)

2. **Analysis Run** (`/analysis-runs`)
   - **Phase 1: Validation**
     - Checks for identical scenes (fails immediately if same)
     - Validates database connection (required in production)
     - Checks scene footprint coverage from STAC metadata
   
   - **Phase 2: Coverage Check & Multi-Scene Logic**
     - If single scene covers < 92% of AOI:
       - Searches database for additional scenes
       - Prioritizes low-cloud scenes within 30 days of target
       - Downloads and mosaics multiple tiles
       - Validates final mosaic coverage (must be ≥ 95%)
     - If coverage insufficient: **Fails with HTTP 422** and actionable guidance
   
   - **Phase 3: Processing**
     - Downloads `.tif` bands via `utils/stac_downloader.py`
     - Runs scientific processing via `analysis_pipeline.py`
     - Generates zones and alerts via `alert_rules.py`
     - Saves indices (NDVI, NDWI, BSI) as GeoTIFFs with PNG previews
     - Saves results to database with status tracking

3. **Visualization**
   - Frontend fetches zones as GeoJSON
   - Alerts include geometry for map highlighting
   - Stats aggregated from zone areas
   - Index layers rendered as overlays

## File Structure

```
backend/
├── main.py              # FastAPI app, routes, database, exception handling
├── config.py            # ⭐ Production configuration (coverage, temporal, validation)
├── exceptions.py        # ⭐ Custom exceptions (InsufficientCoverageError, etc.)
├── analysis_pipeline.py # ⭐ NDVI/BSI/NDWI calculations + multi-scene mosaicking
├── alert_rules.py       # Alert generation engine
├── utils/
│   ├── stac_downloader.py     # Imagery download from STAC
│   ├── spatial.py             # Raster/vector operations
│   ├── coverage_validator.py  # Coverage validation utilities
│   ├── mosaicking.py          # ⭐ Multi-scene mosaicking
│   ├── index_generator.py     # Index calculation and preview generation
│   └── imagery_utils.py       # RGB preview generation
├── config/
│   └── alert_rules.json    # Alert thresholds
├── data/
│   ├── minewatch.db        # SQLite database
│   ├── imagery/            # Downloaded .tif bands
│   ├── mosaics/            # Mosaicked tiles (when multi-scene)
│   ├── indices/            # Index GeoTIFFs (NDVI, NDWI, BSI)
│   └── cache/              # PNG previews
└── docs/
    └── storage_strategy.md # Architecture notes

⭐ = New/significantly enhanced for production
```

## Database Schema

- `mine_area` - Site boundary configuration (singleton)
- `imagery_scene` - Registered satellite scenes (includes footprint_geojson for coverage validation)
- `analysis_run` - Analysis execution records with status tracking:
  - `completed` - Successfully completed
  - `failed_coverage` - Insufficient imagery coverage
  - `failed_identical_scenes` - Same scene used for baseline and latest
  - `failed_mosaic` - Mosaicking failed
  - `failed` - Other errors
- `analysis_zone` - Change detection polygons (replaces `detected_zone`)
- `alert` - Generated alerts with geometry for map visualization

## Production Features

### Multi-Scene Mosaicking
Automatically combines multiple satellite tiles when needed:
- Triggered when single scene coverage < 92%
- Searches database for additional scenes
- Prioritizes low-cloud scenes within 30 days
- Downloads and mosaics bands seamlessly
- Validates final coverage (≥ 95% required)

### Coverage Validation
Three-stage validation ensures quality:
1. **Pre-download:** Checks STAC footprints
2. **Post-download:** Validates actual pixel data
3. **Post-mosaic:** Ensures combined coverage meets requirements

### Error Handling
Graceful failures with detailed context:
- `InsufficientCoverageError` - Includes coverage %, scene count, guidance
- `IdenticalScenesError` - Caught before any processing
- `MosaicError` - Band-specific failure details
- All errors update database with specific failure status

### Configuration
Centralized in `backend/config.py`:
```python
# Coverage thresholds
COVERAGE_CONFIG = {
    "MINIMUM_REQUIRED": 95.0,   # Hard requirement
    "MOSAIC_THRESHOLD": 92.0,   # Triggers multi-scene
}

# Temporal constraints
TEMPORAL_CONFIG = {
    "MAX_DATE_DIFF_DAYS": 30.0  # Max days between scenes
}

# Scene selection
SCENE_CONFIG = {
    "MAX_CLOUD_COVER": 80.0,    # Skip cloudier scenes
    "PREFER_LOW_CLOUD": True    # Prioritize clear scenes
}
```

See `PRODUCTION_READY_SUMMARY.md` for complete documentation.

