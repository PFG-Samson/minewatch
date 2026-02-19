# MineWatch Technical Documentation

> **Version**: Derived from codebase as of 2026-02-19. All statements are traceable to source files.
> **Audience**: Developers, DevOps operators, environmental analysts, system auditors.

---

## 1. System Purpose

MineWatch is an environmental monitoring platform for active mining sites. It automates the detection of land-cover change by comparing satellite imagery acquired at two different points in time over a user-defined Area of Interest (AOI).

The real-world problem it solves:

- Mining operations cause vegetation loss, expansion of bare soil (excavation), and accumulation of water in unauthorized areas. Manual inspection of these changes is slow, expensive, and spatially imprecise.
- MineWatch automates this workflow by ingesting Sentinel-2 multispectral satellite imagery, computing spectral change indices (NDVI, NDWI, BSI) between a baseline and a latest acquisition, and generating spatially explicit alerts when change thresholds are exceeded.

The platform supports:

1. Configuring an AOI polygon (mine boundary) with a buffer zone.
2. Ingesting satellite scenes for that AOI from Microsoft Planetary Computer's STAC catalog.
3. Running change detection analysis between two temporal acquisitions.
4. Reviewing detected change zones and alerts on a map-based dashboard.
5. Exporting PDF reports with imagery, index statistics, zone areas, and alert summaries.

---

## 2. High-Level Architecture

### Components

| Component | Technology | Role |
|---|---|---|
| **Frontend** | React 18, TypeScript, Vite, Leaflet, TailwindCSS | Interactive map dashboard and data entry UI |
| **Backend API** | FastAPI (Python), Uvicorn | REST API exposing all system operations |
| **Database** | SQLite 3 (WAL mode) | Persists mine area, scenes, runs, zones, alerts |
| **Processing Pipeline** | NumPy, Rasterio, Shapely, PyProj | Spectral index calculation, clipping, resampling, change detection |
| **Imagery Provider** | Microsoft Planetary Computer (STAC API) | Sentinel-2 L2A imagery source |
| **Static File Server** | FastAPI StaticFiles | Serves cached PNG previews and GeoTIFF indices |

### Data Flow: Lifecycle of a Dataset

```
User defines AOI boundary (GeoJSON/KML/KMZ)
        │
        ▼
POST /jobs/ingest-stac
  → Query Planetary Computer STAC API by AOI bounding box
  → Filter by cloud cover (≤ configured threshold, default 20%)
  → Store scene metadata (URI, footprint, acquired_at, cloud_cover) in imagery_scene table
  → Repeat until AOI coverage ≥ min_coverage_percent (default 95%)
        │
        ▼
POST /analysis-runs
  → Select two scenes (baseline + latest) from DB
  → Check single-scene footprint coverage against AOI
  → If coverage < 92%: Epoch-based mosaicking path
      → Build temporal coverage sets (10-minute grouping window)
      → Select latest two valid epochs (≥80% AOI coverage each)
      → Download Sentinel-2 bands B02, B03, B04, B08, B11 from Planetary Computer
      → Sign asset URLs via PC SAS token API
      → Create per-band mosaics using rasterio.merge
      → Clip mosaics to AOI boundary
  → If coverage ≥ 92%: Single-scene fast path
      → Download bands with AOI coverage validation
        │
        ▼
  → Clip & Resample (Stage 2)
      → B04 (Red) establishes target spatial grid
      → All other bands resampled to match via bilinear reprojection
        │
        ▼
  → Index Calculation (Stage 3)
      → NDVI = (NIR - RED) / (NIR + RED)         [B08, B04]
      → NDWI = (GREEN - NIR) / (GREEN + NIR)     [B03, B08]
      → BSI  = ((SWIR+RED)-(NIR+BLUE)) / ((SWIR+RED)+(NIR+BLUE))  [B11, B04, B08, B02]
        │
        ▼
  → Preview & Change Layer Generation (Stage 4)
      → Colormapped PNG previews saved to backend/data/cache/
      → GeoTIFF index files saved to backend/data/indices/
      → Change rasters = latest - baseline for each index
        │
        ▼
  → Change Detection & Zone Extraction (Stage 5)
      → Vegetation loss mask: ΔNDVI > 0.15
      → Mining expansion mask: ΔBSI > 0.25
      → Water accumulation mask: ΔNDWI > 0.20
      → Binary masks vectorized to GeoJSON polygons
      → Zones stored in analysis_zone table
        │
        ▼
  → Alert Rule Evaluation
      → AlertRuleEngine evaluates each zone against configured rules
      → Area-based severity thresholds applied per rule type
      → Alerts stored in alert table with geometry
        │
        ▼
Frontend Dashboard
  → Map displays change zones overlaid on AOI
  → Alert panel lists generated alerts with severity
  → Satellite Imagery view shows RGB previews (baseline + latest)
  → Index layers (NDVI, NDWI, BSI, change) toggleable on map
  → GET /analysis-runs/{id}/report → PDF report download
```

---

## 3. Project Structure Breakdown

```
mine-watcher-main/
├── backend/                    # Python FastAPI backend
│   ├── main.py                 # API server, DB schema, route handlers (2016 lines)
│   ├── analysis_pipeline.py    # Core analysis orchestration
│   ├── alert_rules.py          # Rule-based alert engine
│   ├── config.py               # All numeric thresholds and flags
│   ├── exceptions.py           # Domain-specific exception hierarchy
│   ├── requirements.txt        # Python dependencies
│   ├── minewatch.db            # SQLite database (production data file)
│   ├── config/
│   │   └── alert_rules.json    # Configurable alert rule definitions
│   ├── data/
│   │   ├── imagery/            # Downloaded Sentinel-2 band GeoTIFFs
│   │   ├── mosaics/            # Multi-scene mosaic outputs
│   │   ├── indices/            # Index GeoTIFFs (NDVI, NDWI, BSI, change)
│   │   └── cache/              # Colormapped PNG previews
│   └── utils/
│       ├── spatial.py          # Index formulas, clip, vectorize
│       ├── stac_downloader.py  # STAC API client, band download, URL signing
│       ├── coverage_validator.py # AOI coverage calculation
│       ├── mosaicking.py       # Multi-tile merge and clip
│       ├── temporal_grouping.py# Epoch grouping and coverage set selection
│       ├── index_generator.py  # GeoTIFF and PNG output for indices
│       └── imagery_utils.py    # RGB preview generation
├── src/                        # React/TypeScript frontend
│   ├── App.tsx                 # Routing root
│   ├── pages/                  # Top-level page components
│   ├── components/
│   │   ├── dashboard/          # Dashboard views (map, alerts, imagery, analysis, reports)
│   │   ├── landing/            # Landing/home page components
│   │   └── ui/                 # shadcn/ui component library
│   ├── hooks/                  # Custom React hooks
│   └── lib/                    # Utility functions, API client
├── public/                     # Static assets
├── index.html                  # Vite entry point
├── vite.config.ts              # Vite build configuration
└── tailwind.config.ts          # TailwindCSS theme
```

### Key Module Responsibilities

**`main.py`**: Single-file API server. Owns DB schema creation, migration (inline `ALTER TABLE`), all route handlers, report PDF generation via ReportLab, KML/KMZ conversion, STAC search pagination, and static file mounting.

**`analysis_pipeline.py`**: Orchestrates the scientific pipeline. Contains `run_analysis` (production entry point requiring DB connection) and `run_analysis_core` (pure processing, no DB access). Handles the branch logic between single-scene and epoch-based mosaicking paths.

**`config.py`**: Centralizes all tunable parameters. Validates configuration consistency on module import. `calculate_max_scenes_needed()` dynamically scales scene search based on AOI area.

**`temporal_grouping.py`**: Groups scenes into acquisition epochs using a 10-minute tolerance window. Computes combined footprint coverage for each epoch. Returns `CoverageSet` objects used to select baseline and latest epochs.

**`coverage_validator.py`**: Computes intersection area between raster footprints and the AOI polygon. Supports both fast (bounds-only) and accurate (valid-pixel-mask) modes.

**`mosaicking.py`**: Merges multiple same-band GeoTIFFs using `rasterio.merge`. Handles CRS mismatches by reprojecting to the first dataset's CRS. Clips the merged output to the AOI boundary.

---

## 4. Data Sources & Geospatial Handling

### Imagery Provider

- **Provider**: Microsoft Planetary Computer
- **Collection**: `sentinel-2-l2a` (Sentinel-2 Level 2A, atmospherically corrected surface reflectance)
- **STAC endpoint**: `https://planetarycomputer.microsoft.com/api/stac/v1/search`
- **Asset signing**: Each band asset URL is signed via `https://planetarycomputer.microsoft.com/api/sas/v1/sign` to obtain a time-limited access URL. Unsigned URLs are rejected by Azure Blob Storage.

### Bands Used

| Band | Sentinel-2 ID | Resolution | Purpose |
|---|---|---|---|
| Blue | B02 | 10m | BSI calculation |
| Green | B03 | 10m | NDWI calculation |
| Red | B04 | 10m | NDVI, BSI calculation; reference grid |
| NIR | B08 | 10m | NDVI, NDWI, BSI calculation |
| SWIR | B11 | 20m | BSI calculation |

> **Note**: B11 is native 20m resolution. It is resampled to match the B04 (10m) spatial grid via bilinear reprojection during the clip-and-resample stage. This prevents shape mismatches in index arithmetic.

### Coordinate Systems

- **Storage**: All boundary and footprint geometries are stored as WGS84 (EPSG:4326) GeoJSON strings in the database.
- **Processing**: Rasterio clips are performed in the native raster CRS (typically a UTM zone). Geometries are transformed on-the-fly using `rasterio.warp.transform_geom` before masking.
- **Output**: Index GeoTIFFs retain the source UTM CRS. Bounds are converted to EPSG:4326 for frontend consumption via `rasterio.warp.transform_bounds`.
- **Area calculation**: AOI area in the PDF report uses the pyproj `Geod(ellps='WGS84')` geodetic calculator for accurate hectare/km² measurements. Zone area uses a UTM reprojection centered on the zone centroid.

### Tiling Logic

- A single Sentinel-2 tile covers approximately 110km × 110km (~1 degree² at the equator).
- If the AOI boundary spans multiple MGRS tiles, a single scene will have coverage below the 92% mosaic threshold.
- The system detects this via `footprint_coverage_for_uri()` before downloading, then switches to the epoch-based path.
- `calculate_max_scenes_needed()` estimates the number of scenes needed by computing `max(int(area_deg² × 1.5), 2)`, capped at 8.

### Coverage Validation

Two validation modes:

1. **Bounds-only** (`check_valid_data=False`): Uses the raster's bounding box rectangle intersected with the AOI. Fast; used for mosaic validation.
2. **Valid-pixel-mask** (`check_valid_data=True`): Extracts the actual non-zero pixel extent as vector shapes. Slower but eliminates false positives from nodata-padded tiles. Used for post-download validation.

### Scene Selection Rules

1. Scenes are queried by AOI bounding box and cloud cover (`eo:cloud_cover ≤ configured max`, default 20%).
2. Candidate scenes are ordered by proximity to target date, then by cloud cover (ascending).
3. Scenes more than 30 days from the target date are skipped.
4. Scenes with cloud cover >80% are skipped (configurable).
5. Scenes are added greedily until combined footprint coverage ≥ 95% or the max scene count (8) is reached.

### Metadata Handling

- Scene URI is the STAC item ID (e.g., `S2A_MSIL2A_20231015T103021_N0509_R108_T32UQD_20231015T145215`).
- URI is parsed with regex `^(S2[AB])_MSI(L2A)_.+?_T([0-9A-Z]{5})` to extract platform (S2A/S2B), processing level, and MGRS tile code for display in PDF reports.
- Footprint GeoJSON (scene boundary polygon in WGS84) is stored per scene and used for all coverage intersection calculations.

---

## 5. Database Design

The database is SQLite 3 located at `backend/minewatch.db`. WAL journaling mode is enabled on every connection for concurrent-read safety.

### Tables

#### `mine_area`
Enforced as singleton (CHECK `id = 1`). Stores the user's monitored AOI.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Always 1 (singleton constraint) |
| `name` | TEXT | Display name for the site |
| `description` | TEXT | Optional free-text description |
| `boundary_geojson` | TEXT | GeoJSON string of the AOI polygon |
| `buffer_km` | REAL | Buffer zone around boundary in km |
| `created_at` | TEXT | ISO 8601 UTC timestamp |
| `updated_at` | TEXT | ISO 8601 UTC timestamp |

#### `imagery_scene`
One row per Sentinel-2 STAC item ingested.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `source` | TEXT | STAC collection name (e.g., `sentinel-2-l2a`) |
| `acquired_at` | TEXT | Scene acquisition datetime (ISO 8601) |
| `cloud_cover` | REAL | Cloud cover percentage from STAC properties |
| `footprint_geojson` | TEXT | Scene extent polygon in WGS84 |
| `uri` | TEXT | STAC item ID used to download bands |
| `created_at` | TEXT | Ingestion timestamp |

#### `analysis_run`
One row per analysis execution.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `baseline_date` | TEXT | Optional user-supplied baseline date |
| `latest_date` | TEXT | Optional user-supplied latest date |
| `baseline_scene_id` | INTEGER FK | References `imagery_scene.id` |
| `latest_scene_id` | INTEGER FK | References `imagery_scene.id` |
| `status` | TEXT | `completed`, `failed`, `failed_coverage`, `failed_identical_scenes`, `failed_mosaic` |
| `created_at` | TEXT | Run creation timestamp |

#### `analysis_zone`
One row per detected change polygon.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `run_id` | INTEGER FK | References `analysis_run.id` |
| `zone_type` | TEXT | `vegetation_loss`, `mining_expansion`, `water_accumulation` |
| `area_ha` | REAL | Area of the polygon in hectares |
| `geometry_geojson` | TEXT | GeoJSON polygon in WGS84 |

#### `alert`
One row per generated alert.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `run_id` | INTEGER FK | References `analysis_run.id` |
| `alert_type` | TEXT | `vegetation_loss`, `excavation_alert`, `water_warning`, `boundary_breach` |
| `title` | TEXT | Human-readable alert title |
| `description` | TEXT | Detailed description text |
| `location` | TEXT | Descriptive location label |
| `severity` | TEXT | `high`, `medium`, `low` |
| `geometry_geojson` | TEXT | GeoJSON geometry of the affected area |
| `created_at` | TEXT | Alert creation timestamp |

### Migrations

Schema migrations are applied inline at startup in `init_db()` using `PRAGMA table_info()` to detect missing columns. No external migration tool is used.

- `analysis_run.baseline_scene_id/latest_scene_id` added if absent.
- `mine_area.description` added if absent.
- `alert.geometry_geojson` added if absent.

### Spatial Data Storage

No PostGIS or spatial indexing is used. All spatial operations are performed in-memory using Shapely after loading GeoJSON strings from the database. Coverage intersection is a pure Python/Shapely operation. For large AOIs with many candidate scenes, this may become a performance bottleneck.

---

## 6. Processing & Analytical Algorithms

### Stage 1 — Scene Selection and Data Acquisition

**Trigger**: `POST /analysis-runs` with two valid scene IDs.

**Inputs**: Baseline and latest `ImageryScene` records, mine area boundary GeoJSON, up to 50 candidate scenes from DB.

**Decision Logic — Single-scene vs. Epoch path**:
- For each selected scene, `footprint_coverage_for_uri()` fetches the scene footprint from the Planetary Computer STAC API and computes AOI intersection.
- If either scene covers < 92% of the AOI, the epoch-based mosaicking path is taken.
- Otherwise, the single-scene fast path is used.

**Epoch-based path**:
1. `build_coverage_sets_from_candidates()` groups the 50 most recent scenes into epochs using a 10-minute acquisition tolerance window.
2. Each epoch's combined footprint is intersected with the AOI. Epochs with < 80% coverage are discarded.
3. The two most recent valid epochs are selected as latest and baseline.
4. Bands are downloaded for all scenes in each epoch, then mosaicked per band.

**Single-scene path**:
- `download_sentinel2_bands_with_validation()` downloads 5 bands per scene and verifies coverage.
- Coverage check uses raster bounds only (fast mode), with a minimum of 80%.

**Failure behavior**: `InsufficientCoverageError` is raised if fewer than 2 valid epochs exist or post-mosaic coverage is below 95%. The run status is set to `failed_coverage`. `MosaicError` is raised if any band mosaic fails; status becomes `failed_mosaic`.

**Assumptions**: Bands are downloaded from Microsoft Planetary Computer. Asset URLs must be signed. Files are cached to disk and reused if already present (file existence check before download).

---

### Stage 2 — Clip & Resample

**Trigger**: Bands downloaded or mosaics ready.

**Inputs**: File paths for B02, B03, B04, B08, B11 (baseline and latest sets).

**Processing**:
1. B04 (Red) is clipped first. Its output `(shape, transform, CRS)` becomes the reference grid.
2. All remaining bands — including the 20m-native B11 — are clipped and bilinearly resampled to match the B04 grid using `rasterio.warp.reproject`.

**Outputs**: Five NumPy 2D arrays per epoch, all at identical dimensions and spatial alignment.

**Failure behavior**: Any raster I/O exception propagates as a general exception, which is caught by the route handler and stored as `status = 'failed'`.

**Assumptions**: Baseline and latest scenes are from the same MGRS grid zone (or mosaics have been uniformly reprojected). The AOI must be in WGS84.

---

### Stage 3 — Index Calculation

All calculations are performed on float64 NumPy arrays. Division-by-zero and NaN values are suppressed using `np.errstate(divide='ignore', invalid='ignore')` and replaced with 0.0.

#### NDVI (Normalized Difference Vegetation Index)
```
NDVI = (NIR − RED) / (NIR + RED)     [bands B08, B04]
```
Range: -1 to 1. High positive values indicate dense vegetation. Values near 0 or negative indicate bare soil, water, or urban surfaces.

#### NDWI (Normalized Difference Water Index)
```
NDWI = (GREEN − NIR) / (GREEN + NIR)   [bands B03, B08]
```
Range: -1 to 1. Positive values indicate open water. Used here to detect new water accumulation (e.g., tailings ponds, drainage failures).

#### BSI (Bare Soil Index)
```
BSI = ((SWIR + RED) − (NIR + BLUE)) / ((SWIR + RED) + (NIR + BLUE))   [bands B11, B04, B08, B02]
```
Range: -1 to 1. High positive values indicate exposed bare soil. Used to detect mining expansion and excavation.

---

### Stage 4 — Preview and Change Layer Generation

**Trigger**: `save_indices=True` (always true for production runs).

For each index type and for each of (baseline, latest, change):
- A GeoTIFF is written to `backend/data/indices/run{id}_{prefix}_{index}.tif` with LZW compression.
- A colormapped PNG preview is written to `backend/data/cache/run{id}_{prefix}_{index}.png`.
- Colormaps are piecewise linear interpolations (8-stop gradients defined in `COLORMAPS` dict).
- Change layers use a diverging red-white-green colormap.
- A 256-entry lookup table is precomputed for vectorized pixel-to-color mapping.

---

### Stage 5 — Change Detection and Zone Extraction

**Change thresholds** (hardcoded in `run_analysis_core`):

| Zone Type | Condition | Threshold |
|---|---|---|
| `vegetation_loss` | baseline NDVI − latest NDVI | > 0.15 |
| `mining_expansion` | latest BSI − baseline BSI | > 0.25 |
| `water_accumulation` | latest NDWI − baseline NDWI | > 0.20 |

**Vectorization**: `rasterio.features.shapes()` converts the boolean mask to vector polygons. Each polygon is reprojected from the raster's native UTM CRS back to WGS84 via `rasterio.warp.transform_geom`.

**Area calculation**: Each polygon is reprojected to its local UTM zone using its centroid longitude, and area is computed in m² then converted to hectares.

---

### Alert Rule Engine

**Trigger**: Immediately after zone extraction during each analysis run.

**Configuration**: `backend/config/alert_rules.json`. If the file is missing, hardcoded defaults are used.

**Rules**:

| Rule Class | Zone Type | Min Area (ha) | Severity Levels |
|---|---|---|---|
| `VegetationLossRule` | `vegetation_loss` | 0.2 | low ≥0.2, medium ≥0.5, high ≥1.0 |
| `MiningExpansionRule` | `mining_expansion` | 0.05 | low ≥0.05, medium ≥0.1 |
| `WaterAccumulationRule` | `water_accumulation` | 0.05 | low ≥0.05 (default if no threshold matched) |
| `BoundaryBreachRule` | Any zone type | N/A | high (if zone outside buffered boundary) |

**Decision logic**: Each zone is evaluated against every enabled rule. A zone produces an alert if: it matches the rule's zone_type, its area exceeds `min_area_ha`, and a severity threshold is met. The boundary breach rule performs a geometric `within()` test against the AOI plus buffer polygon.

**Failure behavior**: Rule evaluation exceptions are caught per-rule and logged; they do not abort the run.

---

## 7. API Documentation

The backend runs on `http://localhost:8000`. CORS is configured to allow only `http://localhost:8080`.

### Health

#### `GET /health`
Returns `{"status": "ok"}`. No parameters. Used for liveness checks.

---

### Mine Area

#### `GET /mine-area`
Returns the configured AOI. Calculates approximate area in hectares using a degree-to-metre conversion.

**Response** (`MineAreaOut`):
```json
{
  "name": "string",
  "description": "string | null",
  "boundary": { /* GeoJSON */ },
  "buffer_km": 2.0,
  "created_at": "ISO8601",
  "updated_at": "ISO8601",
  "area_ha": 1234.56
}
```
**Error**: `404` if mine area not configured.

#### `PUT /mine-area`
Creates or replaces the mine area. Only one record is ever stored (id=1).

**Request body** (`MineAreaUpsert`):
```json
{
  "name": "My Mine",
  "description": "Optional description",
  "boundary": { /* GeoJSON geometry/feature/featurecollection */ },
  "buffer_km": 2.0
}
```
**Notes**: The boundary must be valid GeoJSON. The `buffer_km` is stored but used only for display and for the `BoundaryBreachRule` geometric test (converted to approximate degrees by dividing by 111.0).

---

### Boundary Conversion

#### `POST /convert-boundary`
Converts uploaded boundary file to GeoJSON. Accepts multipart file upload.

**Supported formats**: `.geojson`, `.json`, `.kml`, `.kmz`

**KML/KMZ handling**: Extracts Placemark elements supporting Point, LineString, Polygon geometries. KMZ files are decompressed first; the first `.kml` file inside is processed.

**Response**:
```json
{
  "success": true,
  "format": "kml",
  "geojson": { /* GeoJSON FeatureCollection */ }
}
```
**Errors**: `400` for unsupported format, invalid XML, empty geometry, or parse failure.

---

### Imagery Scenes

#### `POST /jobs/ingest-stac`
Searches the Planetary Computer STAC catalog and ingests matching Sentinel-2 scenes. Paginates results in batches of 50 until coverage target is met or `max_items` is reached.

**Request body** (`StacIngestJobCreate`):
```json
{
  "collection": "sentinel-2-l2a",
  "max_items": 50,
  "cloud_cover_lte": 20.0,
  "ensure_coverage": true,
  "min_coverage_percent": 95.0
}
```
**Side effects**: Inserts new rows into `imagery_scene`. Skips scenes already present (deduplication by URI). Commits after batch completes.

**Response**: Array of `ImagerySceneOut` for newly created records only.

**Error**: `400` if mine area not configured; `400` if AOI bbox cannot be extracted.

**Performance**: Each batch makes one STAC POST request. Coverage computation runs after every batch (Shapely union of all footprints).

---

#### `POST /imagery`
Manually creates an `imagery_scene` record.

**Request body** (`ImagerySceneCreate`):
```json
{
  "source": "Sentinel-2",
  "acquired_at": "2024-01-15T10:00:00Z",
  "cloud_cover": 5.3,
  "footprint": { /* GeoJSON geometry */ },
  "uri": "S2A_MSIL2A_..."
}
```

#### `GET /imagery`
Lists scenes ordered by `acquired_at DESC`. Default limit 50, configurable via `?limit=N`.

#### `GET /imagery/latest`
Returns the most recently acquired scene.

#### `GET /imagery/latest/preview`
Returns an RGB preview PNG URL for the most recent scene if B02/B03/B04 files are already downloaded. Returns `{"preview": null}` with a message if bands are not yet on disk.

#### `GET /imagery/scenes`
Simplified scene list without footprint data, for frontend dropdowns. Default limit 20.

---

### Analysis Runs

#### `POST /analysis-runs`
**The primary endpoint**. Creates and immediately executes a complete analysis run synchronously.

**Request body** (`AnalysisRunCreate`):
```json
{
  "baseline_date": "2023-06-01",
  "latest_date": "2024-01-15",
  "baseline_scene_id": 5,
  "latest_scene_id": 12
}
```
If scene IDs are omitted, the two most recently acquired scenes are selected automatically.

**Side effects**:
- Triggers the full analysis pipeline (download, mosaic, clip, indices, change detection, alert evaluation).
- Inserts: one `analysis_run`, N `analysis_zone` rows, M `alert` rows.
- Writes GeoTIFFs to `data/indices/` and PNGs to `data/cache/`.
- Run status is updated to reflect failures.

**Response**: `AnalysisRunOut` (run metadata only; zones and alerts are queried separately).

**Error codes**:
| Code | Condition |
|---|---|
| `422` | `insufficient_coverage` — AOI not fully covered |
| `400` | `identical_scenes` — baseline and latest are the same scene |
| `500` | `mosaic_failed` — rasterio merge error |
| `500` | `AnalysisError` / `DatabaseConnectionError` — general pipeline failure |

**Performance**: This is a long-running synchronous operation (seconds to minutes depending on download speed and AOI size). No async job queue exists; the HTTP request blocks until completion.

#### `GET /analysis-runs`
Lists runs ordered by `created_at DESC`. Default limit 50.

#### `GET /analysis-runs/{run_id}`
Returns run metadata plus all associated zones as a GeoJSON FeatureCollection.

**Response structure**:
```json
{
  "run": { "id": 1, "baseline_date": "...", "latest_date": "...", "status": "completed", "created_at": "..." },
  "zones": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "id": 1,
        "properties": { "zone_type": "vegetation_loss", "area_ha": 2.3 },
        "geometry": { /* GeoJSON polygon */ }
      }
    ]
  }
}
```

#### `GET /analysis-runs/latest/stats`
Returns aggregated zone area totals for the most recent run. Used to populate the dashboard summary cards.

**Response includes**: `vegetation_loss_ha`, `mining_expansion_ha`, `water_accumulation_ha`, `total_change_ha`, `last_updated`, dates.

#### `GET /analysis-runs/{run_id}/imagery`
Returns RGB preview URLs and bounds for the baseline and latest scenes in a run. Checks both the per-scene imagery directory and the mosaic directory for band files.

**Response**:
```json
{
  "baseline": { "url": "/data/cache/preview_...", "bounds": [...] },
  "latest": { "url": "/data/cache/preview_...", "bounds": [...] }
}
```

#### `GET /analysis-runs/{run_id}/indices`
Returns URL and geographic bounds for all 9 index layers (3 indices × 3 time slots: baseline, latest, change). Returns `null` for layers whose PNG file does not exist.

#### `GET /analysis-runs/{run_id}/report`
Generates and returns a PDF report as an attachment.

**Report contents**: Site metadata (name, area, centroid, bbox, buffer), run metadata, scene details (platform, tile, cloud cover, URI), coverage percentages, baseline/latest RGB previews, NDVI/NDWI/BSI index visuals with colormaps and legends, index statistics table (mean per index per epoch), zones summary table, alerts table, alert rule configuration snapshot.

**Performance**: PDF is written to disk at `data/cache/report_run{id}.pdf` then streamed as bytes. The report generation reads from GeoTIFF files to compute index statistics. Slow if index files do not exist.

**Response**: `application/pdf` with `Content-Disposition: attachment`.

#### `DELETE /analysis-runs/clear-all`
Deletes all analysis records and physical data files. Removes:
- All rows from `alert`, `analysis_zone`, `analysis_run`, `imagery_scene`.
- All files in `data/imagery/` and `data/cache/`.

**Warning**: This is irreversible and removes all downloaded band data.

---

### Alerts

#### `GET /alerts`
Lists all alerts across all runs, ordered by `created_at DESC`. Default limit 50.

**Response**: Array of `AlertOut` including geometry for each alert.

---

### Alert Rules

#### `GET /alert-rules`
Returns the current `alert_rules.json` configuration as JSON.

#### `PUT /alert-rules`
Replaces the alert rule configuration. Immediately reloads rules.

**Request body** (`AlertRulesUpdate`):
```json
{
  "rules": {
    "vegetation_loss": {
      "enabled": true,
      "min_area_ha": 0.2,
      "thresholds": { "high": 1.0, "medium": 0.5, "low": 0.2 },
      "messages": { "high": "Significant vegetation loss ({area:.1f} ha)", ... },
      "description_template": "NDVI analysis shows decline."
    }
  },
  "global_settings": {}
}
```

---

### Static Files

| Mount Path | Source Directory | Content |
|---|---|---|
| `/data/cache/` | `backend/data/cache/` | Colormapped PNG previews |
| `/data/indices/` | `backend/data/indices/` | Index GeoTIFF files |

---

## 8. Operational Workflows

### Workflow 1: Initial Site Setup
1. Navigate to Mine Area configuration in the frontend.
2. Upload a boundary file (GeoJSON, KML, or KMZ) via `POST /convert-boundary` or enter coordinates directly.
3. Set site name, description, and buffer distance.
4. Submit via `PUT /mine-area`.

### Workflow 2: Ingesting Satellite Data
1. Navigate to the Satellite Imagery view.
2. Trigger STAC ingestion via `POST /jobs/ingest-stac` (default: sentinel-2-l2a, ≤20% cloud, 50 max items, ensure 95% coverage).
3. The system paginates the Planetary Computer catalog until the AOI is covered.
4. Ingested scenes appear in the scene list, selectable for analysis.

### Workflow 3: Running Change Detection Analysis
1. Navigate to Change Analysis view.
2. Select a baseline scene and a latest scene from dropdowns (scenes ordered by acquisition date).
3. Trigger analysis via `POST /analysis-runs`.
4. Wait for completion (synchronous operation, may take several minutes on first run due to downloads).
5. On completion, change zones appear on the map and alerts are listed in the Alerts panel.

### Workflow 4: Reviewing Alerts
1. Navigate to the Alerts panel.
2. Each alert shows severity (high/medium/low), type, description, and associated run.
3. Clicking an alert on the map zooms the viewport to the alert's GeoJSON geometry.

### Workflow 5: Analyzing Index Layers
1. Navigate to the Satellite Imagery or Change Analysis view.
2. Toggle index layers (NDVI, NDWI, BSI — baseline, latest, change) using map layer controls.
3. Layers are displayed as geo-referenced PNG overlays using their stored bounds.

### Workflow 6: Exporting a Report
1. Navigate to the Reports view.
2. Select an analysis run.
3. Click Export to trigger `GET /analysis-runs/{run_id}/report`.
4. The browser downloads a PDF file named `minewatch-{site-name}-run-{id}.pdf`.

---

## 9. Deployment & Infrastructure

### Backend

**Runtime**: Python 3.11+ with the dependencies listed in `backend/requirements.txt`:

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | 0.115.6 | REST API framework |
| `uvicorn[standard]` | 0.30.6 | ASGI server |
| `pydantic` | 2.10.3 | Request/response validation |
| `rasterio` | ≥1.4.2 | Raster I/O, clip, mosaic, reproject |
| `numpy` | ≥2.1.0 | Pixel-level array math |
| `shapely` | ≥2.0.6 | Vector geometry operations |
| `pyproj` | ≥3.7.0 | CRS transformation, geodetic area |
| `Pillow` | ≥11.0.0 | PNG preview generation |
| `requests` | 2.32.3 | STAC API HTTP client |
| `pystac-client` | ≥0.8.2 | STAC client library (imported but STAC search implemented manually) |
| `reportlab` | 4.2.5 | PDF generation |
| `fiona` | ≥1.10.1 | Geospatial vector I/O (indirect dep) |

**Starting the backend**:
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

The `if __name__ == "__main__"` block in `main.py` also supports direct execution:
```bash
python -m backend.main
```

**Database**: `backend/minewatch.db` is created automatically by `init_db()` on startup. No external database server required.

### Frontend

**Runtime**: Node.js with Bun lockfile.

**Starting the frontend**:
```bash
npm run dev    # Vite dev server on port 8080 (default)
```

**Building for production**:
```bash
npm run build
```

**Key configuration**: Vite proxies frontend at `localhost:8080`. Backend CORS allows only this origin. Any change to the frontend port requires updating `allow_origins` in `main.py`.

### Environment Variables

No `.env` file is present or read by the application. Configuration is entirely code-based (`config.py`, `alert_rules.json`). No API keys are required; Microsoft Planetary Computer's STAC API and Sentinel-2 assets are publicly accessible (with SAS token signing, which is also unauthenticated).

### Data Directories

These directories are created automatically on startup if absent:

| Path | Created by | Notes |
|---|---|---|
| `backend/data/imagery/` | `stac_downloader.py` | Downloaded band GeoTIFFs, ~50–200MB each |
| `backend/data/mosaics/` | `mosaicking.py` | Merged and clipped mosaics |
| `backend/data/indices/` | `index_generator.py` | Per-run index GeoTIFFs |
| `backend/data/cache/` | `imagery_utils.py`, `index_generator.py` | PNG previews, PDF reports |

### Scheduled Jobs

There are **no scheduled jobs or background workers** in the current codebase. All ingestion and analysis is triggered synchronously by API calls.

### Scaling Considerations

- The SQLite database does not support true concurrent writes. WAL mode and a 30-second timeout mitigate — but do not eliminate — write contention if multiple analysis runs are submitted simultaneously.
- `PARALLEL_DOWNLOADS` in `config.py` is set to `False` to avoid rate limiting from Planetary Computer.
- There is no job queue, so long-running analysis requests tie up an HTTP worker thread. For production deployments with multiple concurrent users, a task queue (Celery, RQ, or FastAPI BackgroundTasks) would be required.
- Rasterio operations are CPU-bound and single-threaded per analysis run.

---

## 10. Failure Modes & Limitations

### Coverage Failures

- **Cause**: AOI boundary spans multiple Sentinel-2 tiles, or the mine is in a region with persistent cloud cover.
- **Symptom**: `POST /analysis-runs` returns HTTP 422 with `error: "insufficient_coverage"`.
- **Condition**: Combined scene footprint coverage < 95% after all available scenes are exhausted.
- **Impact**: No zones, alerts, or index files are produced for that run.
- **Mitigation**: Re-run STAC ingest, or lower the `MINIMUM_REQUIRED` threshold in `config.py` (acceptable for testing only).

### Mosaic Failures

- **Cause**: CRS reprojection error, memory error on large mosaics, or a GeoTIFF from Planetary Computer is corrupted.
- **Symptom**: HTTP 500 with `error: "mosaic_failed"` and the affected band name.
- **Impact**: Run fails at Stage 1. No analysis is performed.

### Identical Scene Error

- **Cause**: User selects the same scene as both baseline and latest.
- **Symptom**: HTTP 400 with `error: "identical_scenes"`.
- **Impact**: Run fails immediately. No data is downloaded.

### Missing Band Files

- **Cause**: The `data/imagery/` directory was manually cleared, or a previous download was interrupted.
- **Symptom**: `KeyError` or `FileNotFoundError` during Stage 2 (clip & resample).
- **Impact**: Run fails. The specific band paths are logged to stdout.
- **Note**: The downloader checks file existence before downloading; partially downloaded files are not detected.

### Change Detection False Positives

- **Cause**: Phenological variation (seasonal leaf-on/off), atmospheric differences between scenes, or varying sun angle between acquisitions dates far apart.
- **Scale**: The `MAX_BASELINE_LATEST_DIFF_DAYS` (365 days) allows scenes up to one year apart, making seasonal change detection possible.
- **Fixed thresholds**: The change thresholds (NDVI >0.15, BSI >0.25, NDWI >0.20) are static. They are not calibrated to the specific sensor geometry, acquisition season, or regional land cover of any particular site.

### Resolution Mismatch

- **B11 is 20m**: If bilinear resampling to 10m introduces artifacts in BSI calculations, high-frequency spatial patterns may be over- or under-represented.
- **Historical limitation**: Prior to the resampling fix (noted in `verify_resampling_fix.py`), shape mismatches caused `ValueError: operands could not be broadcast together` in the scientific pipeline. This is now resolved.

### STAC API Availability

- All imagery ingestion depends on `planetarycomputer.microsoft.com`. If this endpoint is unavailable, `POST /jobs/ingest-stac` will raise an HTTP exception or timeout after 30 seconds.
- SAS token signing uses a separate Microsoft endpoint; if signing fails, downloads will return HTTP 403.

### Database-on-disk Limitations

- SQLite is a single-file embedded database. It is not suitable for deployments where multiple backend processes run simultaneously or where the data directory is on a network file system.
- There is no backup mechanism in the codebase.

### No Authentication

- The API has no authentication or authorization layer. Any process that can reach `localhost:8000` can read or modify all data, clear the entire database, or trigger downloads.

---

## 11. Glossary

| Term | Definition |
|---|---|
| **AOI** | Area of Interest. The mine boundary polygon defined by the user. Analysis is spatially constrained to this area plus the configured buffer. |
| **STAC** | SpatioTemporal Asset Catalog. An open standard for discovering geospatial data. MineWatch queries the Planetary Computer STAC endpoint to find Sentinel-2 scenes. |
| **Sentinel-2 L2A** | Sentinel-2 Level 2A — atmospherically corrected surface reflectance product from ESA. MineWatch uses this product via Microsoft Planetary Computer. |
| **MGRS Tile** | Military Grid Reference System tile. Sentinel-2 data is organized into ~110km × 110km tiles. An AOI may span multiple tiles, requiring mosaicking. |
| **Epoch** | A group of Sentinel-2 scenes acquired within a 10-minute window, treated as a single temporal observation. Used when mosaicking multiple tiles to cover the AOI. |
| **Coverage** | The percentage of the AOI polygon area that is intersected by a scene's valid data footprint. MineWatch requires ≥95% coverage to proceed with analysis. |
| **Baseline** | The earlier of the two satellite acquisitions used in change detection. Represents the pre-event or reference condition. |
| **Latest** | The more recent of the two satellite acquisitions. Represents the current or post-event condition. |
| **NDVI** | Normalized Difference Vegetation Index. Measures vegetation density. Calculated as `(NIR − RED) / (NIR + RED)`. |
| **NDWI** | Normalized Difference Water Index. Measures water presence. Calculated as `(GREEN − NIR) / (GREEN + NIR)`. |
| **BSI** | Bare Soil Index. Measures exposed bare ground. Calculated as `((SWIR + RED) − (NIR + BLUE)) / ((SWIR + RED) + (NIR + BLUE))`. |
| **Change Detection** | Pixel-wise subtraction of baseline from latest index values, followed by thresholding to identify areas of significant change. |
| **Analysis Zone** | A vector polygon (in WGS84) representing a spatially contiguous area of detected change, classified as vegetation loss, mining expansion, or water accumulation. |
| **Alert** | A database record generated when an analysis zone exceeds the configured area and severity thresholds for its zone type. |
| **Mosaic** | A raster file created by merging multiple overlapping satellite tiles into a single seamless image for a given band. |
| **Footprint** | The actual geographic extent of valid (non-nodata) pixels in a satellite scene, stored as a WGS84 GeoJSON polygon. |
| **GeoTIFF** | A raster file format that embeds geographic metadata (CRS, transform) within a TIFF container. Used for all intermediate and output rasters. |
| **SAS Token** | Shared Access Signature token. Used to sign Microsoft Azure Blob Storage URLs for authenticated access to Planetary Computer assets. |
| **WAL** | Write-Ahead Logging. SQLite journaling mode that allows concurrent reads during a write transaction. Enabled on every database connection in MineWatch. |
| **Run Status** | The outcome state of an `analysis_run`: `completed`, `failed`, `failed_coverage`, `failed_identical_scenes`, or `failed_mosaic`. |
