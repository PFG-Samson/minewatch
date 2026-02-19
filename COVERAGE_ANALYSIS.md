# Multi-Scene Coverage System Analysis
## MineWatch - Ensuring Complete AOI Coverage

---

## Executive Summary

The system **DOES have multi-scene mosaicking capabilities** but has **critical gaps** that could allow partial-coverage analyses to proceed. This analysis identifies 15 issues ranging from critical to minor, with actionable recommendations.

**Overall Assessment**: 🟡 **Partially Robust** - Works for ideal cases but needs hardening for edge cases.

---

## Updates (2026-02-19)

- Centralized coverage thresholds implemented in `backend/config.py`
- Post-mosaic coverage validation added with strict minimum requirement
- Report coverage quality now uses precise footprint intersection; falls back to index bounds when footprints are unavailable
- Deterministic PDF reports include coverage metrics for auditability

---

## System Architecture

### Components
```
1. Coverage Validator (coverage_validator.py)
   └─ Checks raster footprints vs boundary
   └─ Validates single/multi-scene coverage
   └─ Finds optimal scene combinations

2. Mosaicking Engine (mosaicking.py)
   └─ Merges multiple rasters
   └─ Handles CRS mismatches
   └─ Clips to boundary

3. Analysis Pipeline (analysis_pipeline.py)
   └─ Orchestrates coverage checks
   └─ Downloads bands from multiple scenes
   └─ Creates mosaics when needed
```

---

## Critical Issues ⚠️

### 1. **Inconsistent Coverage Thresholds**
**Severity**: HIGH  
**Impact**: System uses different thresholds in different places

**Current State**:
- `run_analysis()`: 90% to decide if mosaic needed
- `_find_covering_scenes()`: 95% target coverage
- `mosaicking.py`: 90% validation
- `download_sentinel2_bands_with_validation()`: 80% minimum

**Problem**: Could decide "no mosaic needed" at 91% coverage, but then expect 95% coverage downstream.

**Recommendation**:
```python
# Create centralized configuration
COVERAGE_CONFIG = {
    "MINIMUM_REQUIRED": 95.0,     # Absolute minimum to proceed
    "MOSAIC_THRESHOLD": 92.0,     # Trigger multi-scene if below this
    "TARGET_COVERAGE": 98.0,      # Ideal goal
    "DOWNLOAD_MINIMUM": 80.0      # Per-scene minimum during download
}
```

---

### 2. **No Post-Mosaic Coverage Validation**
**Severity**: HIGH  
**Impact**: Analysis can proceed with insufficient coverage

**Current Code** (analysis_pipeline.py:228-233):
```python
if result.success and result.output_path:
    output_paths[band] = result.output_path
else:
    # Fallback to first scene's band if mosaic failed
    output_paths[band] = band_paths[band][0]
    print(f"  ⚠️ Mosaic failed for {band}, using first scene")
```

**Problem**: Falls back to first scene WITHOUT validating coverage!

**Recommendation**:
```python
if result.success and result.output_path:
    # Validate final mosaic coverage
    final_coverage = validate_coverage(
        result.output_path,
        boundary_geojson,
        min_coverage_percent=COVERAGE_CONFIG["MINIMUM_REQUIRED"]
    )
    if not final_coverage.is_valid:
        raise InsufficientCoverageError(
            f"Mosaic coverage {final_coverage.coverage_percent:.1f}% "
            f"below minimum {COVERAGE_CONFIG['MINIMUM_REQUIRED']}%"
        )
    output_paths[band] = result.output_path
else:
    # Don't silently fall back - validate or fail
    raise MosaicError(f"Failed to create mosaic for {band}: {result.message}")
```

---

### 3. **Database Dependency Disables Multi-Scene**
**Severity**: HIGH  
**Impact**: Multi-scene logic silently disabled if db_conn is None

**Current Code** (analysis_pipeline.py:316):
```python
baseline_needs_mosaic = baseline_footprint_coverage < 90.0 and db_conn is not None
```

**Problem**: If db_conn is None, system NEVER attempts multi-scene, even with partial coverage.

**Recommendation**:
```python
# Make db_conn required for production analysis
if db_conn is None:
    raise ValueError("Database connection required for coverage validation")

# OR provide alternative scene discovery mechanism
baseline_needs_mosaic = baseline_footprint_coverage < 90.0
if baseline_needs_mosaic and db_conn is None:
    logger.warning("Cannot find additional scenes without database connection")
    # Proceed with single scene but LOG coverage gaps clearly
```

---

### 4. **Insufficient Coverage Proceeds Silently**
**Severity**: HIGH  
**Impact**: Analysis runs on partial data without clear warning

**Current Code** (analysis_pipeline.py:340):
```python
if len(covering_scenes) > 1:
    # ... mosaic multiple scenes
else:
    print(f"  ⚠️ Only 1 scene available - downloading single scene...")
    # Proceeds with single scene regardless of coverage
```

**Problem**: No check if that single scene meets minimum coverage requirements.

**Recommendation**:
```python
if len(covering_scenes) > 1:
    # ... mosaic multiple scenes
else:
    print(f"  ⚠️ Only 1 scene available - validating coverage...")
    single_scene_coverage = _check_scene_footprint_coverage(
        db_conn, covering_scenes[0][1], geometry
    )
    
    if single_scene_coverage < COVERAGE_CONFIG["MINIMUM_REQUIRED"]:
        raise InsufficientCoverageError(
            f"Single scene provides only {single_scene_coverage:.1f}% coverage. "
            f"Minimum required: {COVERAGE_CONFIG['MINIMUM_REQUIRED']}%. "
            f"Please ingest more scenes covering this area."
        )
    # Proceed with single scene
```

---

## High Priority Issues 🔴

### 5. **Cloud Cover Ignored in Scene Selection**
**Current**: `_find_covering_scenes()` only sorts by date proximity  
**Impact**: May select cloudy scenes when clear ones exist

**Recommendation**: Use the existing `find_optimal_scenes()` function which supports cloud cover sorting, or enhance `_find_covering_scenes()`:
```python
def _find_covering_scenes(
    db_conn,
    target_date: str,
    boundary_geojson: dict,
    min_coverage_percent: float = 95.0,
    max_scenes: int = 4,
    prefer_low_cloud: bool = True  # NEW
) -> List[Tuple[int, str]]:
    # Query with cloud cover
    rows = db_conn.execute(
        """
        SELECT id, uri, footprint_geojson, acquired_at, cloud_cover,
               ABS(julianday(acquired_at) - julianday(?)) as date_diff
        FROM imagery_scene
        WHERE footprint_geojson IS NOT NULL
        ORDER BY 
            date_diff ASC,
            COALESCE(cloud_cover, 100) ASC  -- Prefer lower cloud cover
        LIMIT ?
        """,
        (target_date, max_scenes * 3)
    ).fetchall()
```

---

### 6. **No Scene Date Tolerance Enforcement**
**Current**: Could mix scenes from different years if needed for coverage  
**Impact**: Temporal inconsistency in change detection

**Recommendation**:
```python
MAX_DATE_DIFFERENCE_DAYS = 30  # Configurable

for row in rows:
    date_diff = row["date_diff"]
    if date_diff > MAX_DATE_DIFFERENCE_DAYS:
        print(f"  ⚠️ Skipping scene {row['uri']} - {date_diff:.0f} days from target")
        continue
    # ... rest of logic
```

---

### 7. **Footprint vs Actual Data Discrepancy**
**Current**: Pre-download check uses STAC footprints, not actual pixel data  
**Impact**: Footprints can be larger than actual data extent (especially with nodata pixels)

**Recommendation**:
```python
# After downloading, validate actual pixel coverage
def validate_downloaded_coverage(band_paths: Dict[str, str], boundary: dict) -> float:
    """Validate actual pixel data coverage (not just bounds)."""
    # Use first band as reference
    first_band = list(band_paths.values())[0]
    coverage_result = validate_coverage(
        first_band,
        boundary,
        check_valid_data=True  # Check actual pixels, not just bounds
    )
    return coverage_result.coverage_percent

# Call after download
actual_coverage = validate_downloaded_coverage(baseline_paths, geometry)
if actual_coverage < COVERAGE_CONFIG["MINIMUM_REQUIRED"]:
    # Attempt to get more scenes or fail gracefully
```

---

### 8. **Max Scenes Hardcoded at 4**
**Current**: `max_scenes=4` limit in `_find_covering_scenes()`  
**Impact**: What if AOI needs 5+ scenes?

**Recommendation**:
```python
# Make configurable based on AOI size
def calculate_max_scenes_needed(boundary_geojson: dict) -> int:
    """Estimate max scenes needed based on boundary size."""
    from shapely.geometry import shape
    boundary_geom = extract_boundary_geometry(boundary_geojson)
    
    # Sentinel-2 tile is ~110km x 110km
    # Calculate area and estimate scenes needed
    area_deg_sq = boundary_geom.area
    # Rough estimate: 1 scene covers ~1 deg² at equator
    estimated_scenes = max(int(area_deg_sq * 1.5), 2)
    
    return min(estimated_scenes, 10)  # Cap at 10 for performance
```

---

## Medium Priority Issues 🟡

### 9. **Identical Scene Check Too Late**
**Current**: Checks if baseline == latest AFTER coverage validation  
**Impact**: Wastes time on unnecessary checks

**Fix**: Move to beginning of `run_analysis()`:
```python
def run_analysis(...):
    # Early validation - MOVE THIS UP
    if baseline_scene.uri == latest_scene.uri:
        print("\n⚠️  WARNING: Baseline and latest scenes are identical")
        return [], []
    
    # Then proceed with coverage checks...
```

---

### 10. **No User-Facing Coverage Reports**
**Current**: Coverage info only in logs  
**Impact**: Users don't know about gaps

**Recommendation**: Return coverage metadata from `run_analysis()`:
```python
@dataclass
class AnalysisResult:
    zones: List[Zone]
    alerts: List[Alert]
    coverage_metadata: Dict[str, Any]

# Include:
coverage_metadata = {
    "baseline_coverage_percent": baseline_footprint_coverage,
    "latest_coverage_percent": latest_footprint_coverage,
    "baseline_scene_count": len(baseline_scene_uris),
    "latest_scene_count": len(latest_scene_uris),
    "uncovered_areas": uncovered_geojson  # GeoJSON of gaps
}
```

---

### 11. **Not Using `find_optimal_scenes()`**
**Current**: Custom `_find_covering_scenes()` reimplements similar logic  
**Impact**: Code duplication, `find_optimal_scenes()` is unused

**Recommendation**: Consolidate or enhance `find_optimal_scenes()` to work with database queries.

---

## Low Priority Issues 🟢

### 12. **Mosaic File Organization**
- Mosaics: `data/mosaics/`
- Original bands: `data/imagery/`
- Consider unified location or clearer naming

### 13. **Temporary File Cleanup**
- Reprojection creates temp files that may not be cleaned up
- Add explicit cleanup in finally blocks

### 14. **Performance Optimization**
- `_find_covering_scenes()` could batch intersection checks
- Cache footprint geometries

### 15. **Error Messages**
- Improve error messages for debugging
- Include scene IDs, dates, coverage values

---

## Recommended Improvements Priority

### Phase 1: Critical Fixes (Week 1)
1. ✅ Standardize coverage thresholds (Issue #1)
2. ✅ Add post-mosaic validation (Issue #2)
3. ✅ Enforce minimum coverage or fail (Issue #4)
4. ✅ Require db_conn for production (Issue #3)

### Phase 2: High Priority (Week 2)
5. ✅ Add cloud cover consideration (Issue #5)
6. ✅ Enforce date tolerance (Issue #6)
7. ✅ Validate actual pixel data (Issue #7)
8. ✅ Dynamic max scenes calculation (Issue #8)

### Phase 3: Polish (Week 3)
9. ✅ Move identical scene check earlier (Issue #9)
10. ✅ Add coverage reporting to UI (Issue #10)
11. ✅ Consolidate scene selection logic (Issue #11)

### Phase 4: Maintenance
12-15. ✅ File organization, cleanup, performance, error messages

---

## Testing Strategy

### Test Cases to Add:
```python
1. test_single_scene_full_coverage()
   - Single scene covers 100% of AOI

2. test_single_scene_partial_coverage()
   - Single scene covers 75% - should trigger mosaic

3. test_multi_scene_successful_mosaic()
   - 2-3 scenes combine to 95%+ coverage

4. test_insufficient_coverage_fails()
   - Even with all available scenes, <95% coverage - should fail

5. test_cloud_cover_prioritization()
   - Multiple scenes available, prefer low cloud

6. test_temporal_consistency()
   - Reject scenes beyond date tolerance

7. test_mosaic_failure_handling()
   - Mosaic fails - should not silently fall back

8. test_identical_scenes_early_exit()
   - Baseline == Latest - should return immediately

9. test_large_aoi_multiple_tiles()
   - AOI spans 5+ tiles - should handle gracefully

10. test_actual_vs_footprint_coverage()
    - Footprint says 95%, actual data is 80% - should catch
```

---

## Conclusion

**Current State**: The system has the foundational components for intelligent multi-scene handling, but several critical gaps could allow partial-coverage analyses to proceed undetected.

**Recommendation**: Implement Phase 1 critical fixes immediately to ensure production reliability. The system is 70% there but needs hardening.

**Key Insight**: The architecture is sound - the issue is **validation gaps** and **silent failures** rather than missing functionality.

---

## Quick Wins for Immediate Implementation

### 1. Add Global Configuration
```python
# backend/config.py
COVERAGE_CONFIG = {
    "MINIMUM_REQUIRED": 95.0,
    "MOSAIC_THRESHOLD": 92.0,
    "TARGET_COVERAGE": 98.0,
    "MAX_DATE_DIFF_DAYS": 30,
    "MAX_SCENES": 8
}
```

### 2. Add Custom Exception
```python
# backend/exceptions.py
class InsufficientCoverageError(Exception):
    """Raised when imagery doesn't cover the AOI sufficiently."""
    pass
```

### 3. Add Validation Wrapper
```python
def validate_coverage_or_fail(paths, boundary, stage_name):
    """Validate coverage and fail if insufficient."""
    coverage = validate_downloaded_coverage(paths, boundary)
    if coverage < COVERAGE_CONFIG["MINIMUM_REQUIRED"]:
        raise InsufficientCoverageError(
            f"{stage_name} coverage: {coverage:.1f}% "
            f"(required: {COVERAGE_CONFIG['MINIMUM_REQUIRED']}%)"
        )
    return coverage
```

These three additions would prevent most critical issues with minimal code changes.
