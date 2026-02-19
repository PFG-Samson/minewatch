# Changelog

All notable changes to the MineWatch project will be documented in this file.

---

## [2.1.0] - 2026-02-19 - Deterministic PDF Reports

### Added
- Deterministic ReportLab-based PDF generator with strict section order
- Real AOI metrics (geodesic area, perimeter, centroid, bounding box, buffer)
- Precise coverage quality using scene footprints; approximate fallback via index bounds
- Scene details parsing from URI (Platform S2A/S2B, Level L2A, Tile TXXXXX)
- Labeled imagery (Baseline/Latest) and index previews (Baseline/Latest/Change) with colorbar legends and ticks
- Index statistics table (baseline mean, latest mean, delta)
- Structured tables for Zones and Alerts with persistent headers

### Changed
- Removed attachments section from reports to focus on valuable information
- Added Content-Length header to report responses for reliable downloads
- Downsampled previews to avoid large-image warnings and reduce file size

### Fixed
- Resolved zero-byte PDF downloads in some clients
- Fixed a syntax error in report generation code

---

## [2.0.0] - 2026-02-14 - Production-Ready Release 🚀

### Major Features Added

#### ✨ Multi-Scene Mosaicking System
- **Automatic scene combination** when single scene doesn't cover full AOI
- **Intelligent scene selection** based on cloud cover and acquisition date
- **Seamless mosaicking** of multiple satellite tiles with CRS handling
- **Dynamic scene calculation** based on AOI size (2-8 scenes)

#### 🛡️ Comprehensive Coverage Validation
- **Three-stage validation**: Pre-download, post-download, post-mosaic
- **95% minimum coverage** requirement (configurable)
- **Actual pixel data validation** vs just bounds checking
- **Graceful failures** with actionable error messages

#### ⚙️ Centralized Configuration System
- **New `backend/config.py`** module for all thresholds
- **Self-validating configuration** ensures logical consistency
- **Production/development presets** for easy switching
- **Flexible adjustment** for different use cases

#### 🎯 Enhanced Scene Selection
- **Cloud cover filtering**: Skips scenes with >80% cloud cover
- **Date tolerance enforcement**: Max 30 days between scenes in mosaic
- **Low-cloud preference**: Prioritizes clearer scenes automatically
- **Temporal consistency**: Prevents mixing scenes from different seasons

#### 🚨 Production-Grade Error Handling
- **8 custom exception types** with rich context
- **User-friendly error messages** with actionable guidance
- **Database status tracking** for failed analyses
- **Detailed HTTP responses** (422, 400, 500 with context)

### New Files

#### Configuration & Exceptions
- `backend/config.py` - Centralized configuration (159 lines)
- `backend/exceptions.py` - Custom exception hierarchy (295 lines)

#### Documentation
- `PRODUCTION_READY_SUMMARY.md` - Complete production guide (443 lines)
- `COVERAGE_ANALYSIS.md` - Technical analysis of improvements (442 lines)
- `CHANGELOG.md` - This file

### Files Modified

#### Core Pipeline
- `backend/analysis_pipeline.py` (~200 lines changed)
  - Added early validation (identical scenes, db connection)
  - Enhanced `_find_covering_scenes()` with cloud cover and date tolerance
  - Added post-mosaic validation
  - Added single scene coverage validation
  - Standardized all thresholds to use config
  - Added helper functions: `validate_downloaded_coverage()`, `calculate_max_scenes_needed()`, `parse_date()`

#### API Layer
- `backend/main.py` (~80 lines changed)
  - Added comprehensive exception handling in `/analysis-runs` endpoint
  - Returns structured error responses (HTTP 422, 400, 500)
  - Updates database with failure status
  - Imports and uses new custom exceptions

#### Utilities
- `backend/utils/mosaicking.py` (~20 lines changed)
  - Uses `COVERAGE_CONFIG` instead of hardcoded values
  - Enhanced validation in mosaic creation

#### Documentation
- `README.md` - Updated with production features
- `backend/README.md` - Updated with architecture details

### Configuration Changes

#### Coverage Thresholds (Standardized)
```python
# Before: Inconsistent (90%, 95%, 80% in different places)
# After: Centralized in backend/config.py

COVERAGE_CONFIG = {
    "MINIMUM_REQUIRED": 95.0,      # Hard requirement for analysis
    "MOSAIC_THRESHOLD": 92.0,      # Triggers multi-scene mosaicking
    "TARGET_COVERAGE": 98.0,       # Ideal goal
    "DOWNLOAD_MINIMUM": 80.0       # Per-scene minimum
}
```

#### New Temporal Controls
```python
TEMPORAL_CONFIG = {
    "MAX_DATE_DIFF_DAYS": 30.0,    # Max days between scenes in mosaic
}
```

#### New Scene Selection Settings
```python
SCENE_CONFIG = {
    "MAX_SCENES": 8,               # Maximum scenes to combine
    "MAX_CLOUD_COVER": 80.0,       # Skip scenes above this
    "PREFER_LOW_CLOUD": True,      # Prioritize clearer scenes
}
```

#### New Validation Flags
```python
VALIDATION_CONFIG = {
    "CHECK_VALID_DATA": True,              # Check actual pixels vs bounds
    "VALIDATE_POST_MOSAIC": True,          # Validate after mosaicking
    "REQUIRE_DB_CONN": True,               # Required in production
    "FAIL_ON_INSUFFICIENT_COVERAGE": True  # Strict validation
}
```

### API Changes

#### `/analysis-runs` Endpoint Enhanced

**New Error Responses:**

```json
// HTTP 422 - Insufficient Coverage
{
  "error": "insufficient_coverage",
  "message": "User-friendly message with guidance...",
  "coverage_percent": 87.5,
  "required_percent": 95.0,
  "run_id": 123
}

// HTTP 400 - Identical Scenes
{
  "error": "identical_scenes",
  "message": "Baseline and latest scenes are identical...",
  "run_id": 123
}

// HTTP 500 - Mosaic Failed
{
  "error": "mosaic_failed",
  "message": "Failed to create mosaic...",
  "band": "B04",
  "run_id": 123
}
```

**New Run Statuses:**
- `completed` - Success
- `failed_coverage` - Insufficient imagery coverage
- `failed_identical_scenes` - Same scene selected for baseline/latest
- `failed_mosaic` - Mosaicking failed
- `failed` - Other errors

### Database Changes

#### Schema Updates
- `analysis_run.status` - Now tracks specific failure reasons
- No schema migrations required (backward compatible)

### Behavior Changes

#### Breaking Changes
⚠️ **Analysis now fails if coverage < 95%** (previously proceeded with partial coverage)
- **Impact**: Analyses that previously succeeded with 80-94% coverage will now fail
- **Migration**: Run STAC ingestion to get more scenes OR adjust `MINIMUM_REQUIRED` config
- **Benefit**: Ensures data quality and prevents misleading results

⚠️ **Database connection now required in production** (previously optional)
- **Impact**: `db_conn=None` now raises `DatabaseConnectionError`
- **Migration**: Always pass `db_conn` to `run_analysis()` OR set `REQUIRE_DB_CONN=False` for testing
- **Benefit**: Multi-scene mosaicking requires database for scene discovery

#### Non-Breaking Changes
✅ **Multi-scene mosaicking is automatic** - No API changes required
✅ **Scene selection improvements** - Automatically prefer low-cloud scenes
✅ **Identical scene check moved earlier** - Fails immediately, saves processing time

### Performance Impact

#### Overhead Added
- Coverage validation: +2-5 seconds per analysis
- Multi-scene mosaic: Same as before (automatic when needed)
- Error detection: Much faster (catches issues early)

#### Benefits
- Fewer failed analyses (problems caught early)
- Better coverage (automatically finds additional scenes)
- Clearer error messages (easier debugging)

### Testing

#### Manual Test Cases
1. ✅ Single scene with full coverage
2. ✅ Single scene with partial coverage (triggers mosaic)
3. ✅ Multi-scene mosaic success
4. ✅ Insufficient coverage failure
5. ✅ Identical scenes detection
6. ✅ Cloud cover filtering
7. ✅ Date tolerance enforcement

### Migration Guide

#### For Existing Deployments

1. **Backup Database**
   ```bash
   cp backend/minewatch.db backend/minewatch.db.backup
   ```

2. **Update Code**
   ```bash
   git pull origin main
   ```

3. **No Dependency Changes** - All new code uses existing packages

4. **Review Configuration**
   - Check `backend/config.py`
   - Adjust if needed for your use case

5. **Test with Known Data**
   - Run analysis on previously successful scenarios
   - May need to ingest more scenes for some AOIs

6. **Monitor First Runs**
   - Watch for `InsufficientCoverageError`
   - Check logs for coverage percentages

#### Configuration Adjustments

**If 95% is too strict for your AOIs:**
```python
# backend/config.py
COVERAGE_CONFIG["MINIMUM_REQUIRED"] = 90.0
```

**For development/testing:**
```python
# backend/config.py
VALIDATION_CONFIG["REQUIRE_DB_CONN"] = False
VALIDATION_CONFIG["FAIL_ON_INSUFFICIENT_COVERAGE"] = False
```

### Contributors

- Production hardening implementation
- Coverage validation system
- Multi-scene mosaicking
- Error handling and exceptions
- Documentation updates

### References

- See `PRODUCTION_READY_SUMMARY.md` for complete guide
- See `COVERAGE_ANALYSIS.md` for technical deep-dive
- See `README.md` for updated usage instructions

---

## [1.0.0] - Previous Release

### Features
- Basic satellite imagery analysis
- STAC integration
- NDVI, NDWI, BSI calculations
- Change detection
- Alert generation
- PDF reports
- Interactive map

---

**Note:** Version numbering follows [Semantic Versioning](https://semver.org/).
- MAJOR version for incompatible API changes
- MINOR version for added functionality (backward compatible)
- PATCH version for backward compatible bug fixes
