# MineWatch Backend

FastAPI server providing satellite imagery analysis, STAC integration, and alert generation.

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

## Key Endpoints

### Configuration
- `GET /mine-area` - Get mine boundary configuration
- `PUT /mine-area` - Update mine boundary and settings

### Satellite Imagery (STAC)
- `POST /jobs/ingest-stac` - Search STAC catalog, register metadata
- `GET /imagery` - List all registered scenes
- `GET /imagery/latest` - Get most recent scene

### Analysis
- `POST /analysis-runs` - Create new analysis (auto-downloads imagery, runs processing)
- `GET /analysis-runs` - List all runs
- `GET /analysis-runs/{id}` - Get specific run with zones (GeoJSON)
- `GET /analysis-runs/latest/stats` - Get aggregated statistics
- `GET /analysis-runs/{id}/report` - Download PDF report

### Alerts
- `GET /alerts` - List alerts with geometry
- `GET /alert-rules` - Get alert rule configuration
- `PUT /alert-rules` - Update alert thresholds

## Data Flow

1. **STAC Ingestion** (`/jobs/ingest-stac`)
   - Queries Microsoft Planetary Computer
   - Saves scene metadata to `imagery_scene` table
   - Does NOT download imagery files

2. **Analysis Run** (`/analysis-runs`)
   - Downloads `.tif` bands via `utils/stac_downloader.py`
   - Runs scientific processing via `analysis_pipeline.py`
   - Generates zones and alerts via `alert_rules.py`
   - Saves results to database

3. **Visualization**
   - Frontend fetches zones as GeoJSON
   - Alerts include geometry for map highlighting
   - Stats aggregated from zone areas

## File Structure

```
backend/
├── main.py              # FastAPI app, routes, database
├── analysis_pipeline.py # NDVI/BSI/NDWI calculations
├── alert_rules.py       # Alert generation engine
├── utils/
│   ├── stac_downloader.py  # Imagery download from STAC
│   └── spatial.py          # Raster/vector operations
├── config/
│   └── alert_rules.json    # Alert thresholds
├── data/
│   ├── minewatch.db        # SQLite database
│   └── imagery/            # Downloaded .tif bands
└── docs/
    └── storage_strategy.md # Architecture notes
```

## Database Schema

- `mine_area` - Site boundary configuration (singleton)
- `imagery_scene` - Registered satellite scenes
- `analysis_run` - Analysis execution records
- `detected_zone` - Change detection polygons
- `alert` - Generated alerts with metadata

