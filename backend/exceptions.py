"""
Custom Exceptions for MineWatch

Specialized exceptions for coverage validation, mosaicking, and analysis errors.
"""

from __future__ import annotations
from typing import Optional, Dict, Any


class MineWatchError(Exception):
    """Base exception for all MineWatch errors."""
    pass


class CoverageError(MineWatchError):
    """Base exception for coverage-related errors."""
    
    def __init__(
        self, 
        message: str, 
        coverage_percent: Optional[float] = None,
        required_percent: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize coverage error.
        
        Args:
            message: Error description
            coverage_percent: Actual coverage percentage
            required_percent: Required coverage percentage
            metadata: Additional context (scene IDs, dates, etc.)
        """
        super().__init__(message)
        self.coverage_percent = coverage_percent
        self.required_percent = required_percent
        self.metadata = metadata or {}
    
    def __str__(self) -> str:
        """Format error message with coverage details."""
        msg = super().__str__()
        if self.coverage_percent is not None and self.required_percent is not None:
            msg += f" (Coverage: {self.coverage_percent:.1f}%, Required: {self.required_percent:.1f}%)"
        return msg


class InsufficientCoverageError(CoverageError):
    """
    Raised when imagery coverage is below the required threshold.
    
    This error indicates that even after attempting multi-scene mosaicking,
    the available imagery does not adequately cover the Area of Interest (AOI).
    """
    
    def __init__(
        self,
        message: str,
        coverage_percent: float,
        required_percent: float,
        scene_count: int = 1,
        uncovered_area_ha: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize insufficient coverage error.
        
        Args:
            message: Error description
            coverage_percent: Actual coverage percentage achieved
            required_percent: Minimum required coverage percentage
            scene_count: Number of scenes attempted
            uncovered_area_ha: Area not covered in hectares
            metadata: Additional context
        """
        super().__init__(message, coverage_percent, required_percent, metadata)
        self.scene_count = scene_count
        self.uncovered_area_ha = uncovered_area_ha
    
    def get_user_message(self) -> str:
        """
        Get a user-friendly error message with actionable advice.
        
        Returns:
            Formatted message for end users
        """
        msg = (
            f"Insufficient imagery coverage for analysis.\n\n"
            f"Current coverage: {self.coverage_percent:.1f}%\n"
            f"Required coverage: {self.required_percent:.1f}%\n"
            f"Scenes attempted: {self.scene_count}\n"
        )
        
        if self.uncovered_area_ha is not None:
            msg += f"Uncovered area: {self.uncovered_area_ha:.1f} hectares\n"
        
        msg += (
            f"\n"
            f"Action Required:\n"
            f"• Run STAC ingestion to download more satellite scenes\n"
            f"• Ensure scenes cover the entire boundary area\n"
            f"• Consider reducing the boundary size or adjusting the buffer\n"
        )
        
        return msg


class MosaicError(MineWatchError):
    """
    Raised when mosaic creation fails.
    
    This could be due to CRS mismatches, memory issues, or invalid raster data.
    """
    
    def __init__(
        self,
        message: str,
        band_name: Optional[str] = None,
        scene_count: Optional[int] = None,
        original_error: Optional[Exception] = None
    ):
        """
        Initialize mosaic error.
        
        Args:
            message: Error description
            band_name: Name of the band that failed
            scene_count: Number of scenes attempted to mosaic
            original_error: The underlying exception that caused the failure
        """
        super().__init__(message)
        self.band_name = band_name
        self.scene_count = scene_count
        self.original_error = original_error
    
    def __str__(self) -> str:
        """Format error message with mosaic details."""
        msg = super().__str__()
        if self.band_name:
            msg += f" (Band: {self.band_name})"
        if self.scene_count:
            msg += f" (Scenes: {self.scene_count})"
        if self.original_error:
            msg += f" - Caused by: {type(self.original_error).__name__}: {self.original_error}"
        return msg


class TemporalInconsistencyError(MineWatchError):
    """
    Raised when scenes have incompatible acquisition dates.
    
    This prevents mixing imagery from vastly different time periods
    which would compromise change detection analysis.
    """
    
    def __init__(
        self,
        message: str,
        baseline_date: Optional[str] = None,
        latest_date: Optional[str] = None,
        max_allowed_diff_days: Optional[float] = None
    ):
        """
        Initialize temporal inconsistency error.
        
        Args:
            message: Error description
            baseline_date: Baseline acquisition date
            latest_date: Latest acquisition date
            max_allowed_diff_days: Maximum allowed difference in days
        """
        super().__init__(message)
        self.baseline_date = baseline_date
        self.latest_date = latest_date
        self.max_allowed_diff_days = max_allowed_diff_days


class SceneNotFoundError(MineWatchError):
    """
    Raised when a required scene cannot be found or downloaded.
    """
    
    def __init__(
        self,
        message: str,
        scene_uri: Optional[str] = None,
        scene_id: Optional[int] = None
    ):
        """
        Initialize scene not found error.
        
        Args:
            message: Error description
            scene_uri: URI of the missing scene
            scene_id: Database ID of the missing scene
        """
        super().__init__(message)
        self.scene_uri = scene_uri
        self.scene_id = scene_id


class IdenticalScenesError(MineWatchError):
    """
    Raised when baseline and latest scenes are identical.
    
    This prevents meaningless change detection analysis.
    """
    
    def __init__(self, scene_uri: str, acquired_at: Optional[str] = None):
        """
        Initialize identical scenes error.
        
        Args:
            scene_uri: URI of the duplicate scene
            acquired_at: Acquisition date of the scene
        """
        message = (
            f"Baseline and latest scenes are identical: {scene_uri}\n"
            f"Change detection requires different scenes."
        )
        if acquired_at:
            message += f"\nAcquired: {acquired_at}"
        
        super().__init__(message)
        self.scene_uri = scene_uri
        self.acquired_at = acquired_at


class DatabaseConnectionError(MineWatchError):
    """
    Raised when database connection is required but not available.
    """
    
    def __init__(self, message: str = "Database connection required for this operation"):
        super().__init__(message)


class ValidationError(MineWatchError):
    """
    Raised when data validation fails.
    """
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        invalid_value: Optional[Any] = None
    ):
        """
        Initialize validation error.
        
        Args:
            message: Error description
            field_name: Name of the invalid field
            invalid_value: The invalid value
        """
        super().__init__(message)
        self.field_name = field_name
        self.invalid_value = invalid_value


class AnalysisError(MineWatchError):
    """
    Raised when the analysis pipeline encounters an unrecoverable error.
    """
    
    def __init__(
        self,
        message: str,
        stage: Optional[str] = None,
        run_id: Optional[int] = None,
        original_error: Optional[Exception] = None
    ):
        """
        Initialize analysis error.
        
        Args:
            message: Error description
            stage: Analysis stage where error occurred
            run_id: Analysis run ID
            original_error: The underlying exception
        """
        super().__init__(message)
        self.stage = stage
        self.run_id = run_id
        self.original_error = original_error
    
    def __str__(self) -> str:
        """Format error message with analysis details."""
        msg = super().__str__()
        if self.stage:
            msg += f" (Stage: {self.stage})"
        if self.run_id:
            msg += f" (Run ID: {self.run_id})"
        return msg
