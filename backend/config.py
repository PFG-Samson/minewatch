"""
Configuration Module for MineWatch

Centralized configuration for coverage validation, mosaicking, and analysis parameters.
"""

from __future__ import annotations
from typing import Dict, Any


# Coverage Validation Configuration
COVERAGE_CONFIG: Dict[str, float] = {
    # Minimum required coverage to proceed with analysis
    # Analysis will FAIL if coverage is below this threshold
    "MINIMUM_REQUIRED": 95.0,
    
    # Threshold to trigger multi-scene mosaicking
    # If single scene coverage < this, system will attempt to find additional scenes
    "MOSAIC_THRESHOLD": 92.0,
    
    # Target coverage goal (ideal scenario)
    "TARGET_COVERAGE": 98.0,
    
    # Minimum acceptable coverage for individual scene downloads
    # Used during download validation, can be lower since multiple scenes may be combined
    "DOWNLOAD_MINIMUM": 80.0,
}


# Temporal Configuration
TEMPORAL_CONFIG: Dict[str, float] = {
    # Maximum allowed difference in days between target date and selected scenes
    # Prevents mixing scenes from different seasons/years
    "MAX_DATE_DIFF_DAYS": 30.0,
    
    # Maximum allowed difference between baseline and latest dates (in days)
    # For meaningful change detection
    "MAX_BASELINE_LATEST_DIFF_DAYS": 365.0,
}


# Scene Selection Configuration
SCENE_CONFIG: Dict[str, Any] = {
    # Maximum number of scenes to combine in a mosaic
    "MAX_SCENES": 8,
    
    # Default number of scenes to try for mosaic
    "DEFAULT_MAX_SCENES": 4,
    
    # Whether to prefer scenes with lower cloud cover
    "PREFER_LOW_CLOUD": True,
    
    # Maximum cloud cover percentage to consider (scenes above this are skipped)
    "MAX_CLOUD_COVER": 80.0,
    
    # Buffer for scene search (multiplier for initial query)
    "SCENE_SEARCH_MULTIPLIER": 3,
}


# Validation Configuration
VALIDATION_CONFIG: Dict[str, bool] = {
    # Whether to check actual valid data pixels (slower but more accurate)
    # vs just checking raster bounds (faster)
    "CHECK_VALID_DATA": True,
    
    # Whether to validate coverage after mosaicking
    "VALIDATE_POST_MOSAIC": True,
    
    # Whether to require database connection for production analysis
    "REQUIRE_DB_CONN": True,
    
    # Whether to fail analysis if coverage is insufficient
    # Set to False for development/testing only
    "FAIL_ON_INSUFFICIENT_COVERAGE": True,
}


# Performance Configuration
PERFORMANCE_CONFIG: Dict[str, Any] = {
    # Whether to cache footprint geometries for faster lookups
    "CACHE_FOOTPRINTS": True,
    
    # Whether to parallelize band downloads
    "PARALLEL_DOWNLOADS": False,  # Set to True if needed, but may hit rate limits
}


def get_all_config() -> Dict[str, Any]:
    """Returns all configuration as a single dictionary."""
    return {
        "coverage": COVERAGE_CONFIG,
        "temporal": TEMPORAL_CONFIG,
        "scene": SCENE_CONFIG,
        "validation": VALIDATION_CONFIG,
        "performance": PERFORMANCE_CONFIG,
    }


def calculate_max_scenes_needed(area_deg_sq: float) -> int:
    """
    Dynamically calculates maximum scenes needed based on AOI size.
    
    Args:
        area_deg_sq: Area of the boundary in square degrees
        
    Returns:
        Estimated number of scenes needed (capped at MAX_SCENES)
        
    Notes:
        Sentinel-2 tiles are approximately 110km x 110km (~1 degree at equator)
    """
    # Rough estimate: 1 scene covers ~1 deg² at equator
    # Add 50% buffer for overlap and edge cases
    estimated_scenes = max(int(area_deg_sq * 1.5), 2)
    
    # Cap at configured maximum
    return min(estimated_scenes, SCENE_CONFIG["MAX_SCENES"])


def validate_config() -> bool:
    """
    Validates configuration consistency.
    
    Returns:
        True if configuration is valid
        
    Raises:
        ValueError if configuration has logical inconsistencies
    """
    # Coverage thresholds should be ordered correctly
    if COVERAGE_CONFIG["DOWNLOAD_MINIMUM"] > COVERAGE_CONFIG["MOSAIC_THRESHOLD"]:
        raise ValueError(
            "DOWNLOAD_MINIMUM should be <= MOSAIC_THRESHOLD"
        )
    
    if COVERAGE_CONFIG["MOSAIC_THRESHOLD"] > COVERAGE_CONFIG["MINIMUM_REQUIRED"]:
        raise ValueError(
            "MOSAIC_THRESHOLD should be <= MINIMUM_REQUIRED"
        )
    
    if COVERAGE_CONFIG["MINIMUM_REQUIRED"] > COVERAGE_CONFIG["TARGET_COVERAGE"]:
        raise ValueError(
            "MINIMUM_REQUIRED should be <= TARGET_COVERAGE"
        )
    
    # Scene limits should be reasonable
    if SCENE_CONFIG["MAX_SCENES"] < 2:
        raise ValueError("MAX_SCENES should be at least 2")
    
    # Cloud cover should be 0-100
    if not 0 <= SCENE_CONFIG["MAX_CLOUD_COVER"] <= 100:
        raise ValueError("MAX_CLOUD_COVER should be between 0 and 100")
    
    return True


# Validate configuration on module import
validate_config()
