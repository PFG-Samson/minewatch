# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Overview

MineWatch is a satellite-based environmental monitoring application for mining sites. It uses Sentinel-2 imagery to detect land-use changes via spectral indices (NDVI, BSI, NDWI).

## Development Commands

### Frontend (React + Vite + TypeScript)
```sh
npm install          # Install dependencies
npm run dev          # Start dev server at http://localhost:8080
npm run build        # Production build
npm run lint         # ESLint check
npm test             # Run tests once (vitest)
npm run test:watch   # Run tests in watch mode
```

### Backend (FastAPI + Python)
```sh
# Create environment (recommended on Windows with Anaconda)
conda create -p .\.minewatch-env python=3.11 -y
conda activate .\.minewatch-env

# Install dependencies
python -m pip install -r backend/requirements.txt

# Run server at http://localhost:8000
python -m backend.main
```

### Run a single frontend test
```sh
npx vitest run src/test/example.test.ts
```

### Run backend tests
```sh
python backend/test_alert_rules.py
python backend/test_all_indices.py
python backend/test_real_analysis.py
```

## Architecture

### Frontend (`src/`)
- **`lib/api.ts`**: API client with typed functions for all backend endpoints. Add new API calls here.
- **`components/dashboard/`**: Main application views (Dashboard, MapView, AlertsView, ImageryView, etc.)
- **`components/ui/`**: shadcn/ui component library (do not edit directly unless customizing)
- **`hooks/`**: React hooks (`use-toast`, `use-mobile`)
- Uses TanStack Query for data fetching and caching

### Backend (`backend/`)
- **`main.py`**: FastAPI app with all routes and SQLite database initialization
- **`analysis_pipeline.py`**: Orchestrates satellite imagery processing with 6-stage pipeline:
  1. Download & Coverage Validation
  2. Clip & Resample
  3. Index Calculation
  4. Save Indices & Generate Previews
  5. Change Detection & Zone Generation
  6. Alert Generation
- **`alert_rules.py`**: Configurable rule engine for generating alerts from analysis zones. Contains `Zone`, `Alert` dataclasses and rule classes (`VegetationLossRule`, `MiningExpansionRule`, etc.)
- **`config/alert_rules.json`**: Alert threshold configuration (editable without code changes)
- **`utils/`**:
  - `spatial.py`: Raster clipping, index calculations (NDVI, NDWI, BSI), vectorization
  - `stac_downloader.py`: Downloads Sentinel-2 bands from Microsoft Planetary Computer with coverage validation
  - `imagery_utils.py`: RGB preview generation and caching
  - `coverage_validator.py`: Validates imagery coverage over mine boundaries, identifies gaps
  - `mosaicking.py`: Merges multiple satellite tiles when single scene doesn't cover boundary
  - `index_generator.py`: Saves spectral indices as GeoTIFFs, generates colormapped preview PNGs

### Data Flow
1. User uploads GeoJSON boundary via Settings → saved to `mine_area` table
2. STAC ingestion searches Planetary Computer for Sentinel-2 scenes → metadata saved to `imagery_scene` table
3. Analysis run downloads required bands (B02, B03, B04, B08, B11) → clips to AOI → calculates indices → detects changes → generates zones and alerts
4. Frontend displays zones on Leaflet map with layer controls

### Database
- SQLite at `backend/minewatch.db`
- Tables: `mine_area`, `imagery_scene`, `analysis_run`, `analysis_zone`, `alert`
- Uses WAL mode for concurrency

## Key Patterns

- Scientific indices are calculated in `backend/utils/spatial.py` - follow the `(band1 - band2) / (band1 + band2)` normalized difference pattern
- Alert rules follow the Strategy pattern in `alert_rules.py` - create new rules by extending `AlertRule` base class
- Frontend uses React Query mutations for write operations and queries for reads
- GeoJSON geometries are stored as TEXT columns and parsed on read

## External Dependencies

- **Planetary Computer STAC API**: Source for Sentinel-2 imagery (no auth required for unsigned URLs)
- **rasterio + numpy**: Raster processing; requires GDAL (included via rasterio wheel)
- **shapely + pyproj**: Geometry operations and coordinate transforms
