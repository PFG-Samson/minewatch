"""
Alert Rules Engine for MineWatch

Provides rule-based alert generation from analysis zones.
Replaces hardcoded alert logic with configurable, extensible rules.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional
import json
from dataclasses import dataclass
from shapely.geometry import shape
from shapely.ops import unary_union


@dataclass
class Zone:
    """Represents a change detection zone"""
    zone_type: str
    area_ha: float
    geometry: dict[str, Any]


@dataclass
class Alert:
    """Represents a generated alert"""
    alert_type: str
    title: str
    description: str
    location: str
    severity: str  # high, medium, low
    geometry: dict | None = None  # GeoJSON geometry of the affected zone


class AlertRule(ABC):
    """Base class for alert rules"""
    
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.enabled = config.get("enabled", True)
    
    @abstractmethod
    def evaluate(self, zone: Zone, context: dict[str, Any]) -> Optional[Alert]:
        """
        Evaluate if this zone should trigger an alert.
        
        Args:
            zone: The change detection zone
            context: Additional context (mine_area, previous_alerts, etc.)
        
        Returns:
            Alert if rule is triggered, None otherwise
        """
        pass
    
    def _get_severity(self, area_ha: float) -> Optional[str]:
        """Determine alert severity based on area thresholds"""
        thresholds = self.config.get("thresholds", {})
        
        # Check from highest to lowest severity
        if "high" in thresholds and area_ha >= thresholds["high"]:
            return "high"
        elif "medium" in thresholds and area_ha >= thresholds["medium"]:
            return "medium"
        elif "low" in thresholds and area_ha >= thresholds["low"]:
            return "low"
        
        return None


class VegetationLossRule(AlertRule):
    """Alert rule for vegetation loss detection"""
    
    def evaluate(self, zone: Zone, context: dict[str, Any]) -> Optional[Alert]:
        if not self.enabled or zone.zone_type != "vegetation_loss":
            return None
        
        min_area = self.config.get("min_area_ha", 0.2)
        if zone.area_ha < min_area:
            return None
        
        severity = self._get_severity(zone.area_ha)
        if not severity:
            return None
        
        messages = self.config.get("messages", {})
        title = messages.get(severity, f"Vegetation loss detected ({zone.area_ha:.1f} ha)")
        title = title.format(area=zone.area_ha)
        
        desc_template = self.config.get("description_template", "Vegetation loss detected")
        description = desc_template.format(
            area=zone.area_ha,
            ndvi_drop=0.15  # Could be passed in context
        )
        
        return Alert(
            alert_type="vegetation_loss",
            title=title,
            description=description,
            location="Site Assessment Zone",
            severity=severity,
            geometry=zone.geometry
        )


class MiningExpansionRule(AlertRule):
    """Alert rule for mining/excavation expansion"""
    
    def evaluate(self, zone: Zone, context: dict[str, Any]) -> Optional[Alert]:
        if not self.enabled or zone.zone_type != "mining_expansion":
            return None
        
        min_area = self.config.get("min_area_ha", 0.05)
        if zone.area_ha < min_area:
            return None
        
        severity = self._get_severity(zone.area_ha)
        if not severity:
            return None
        
        messages = self.config.get("messages", {})
        title = messages.get(severity, f"Mining expansion detected ({zone.area_ha:.1f} ha)")
        title = title.format(area=zone.area_ha)
        
        desc_template = self.config.get("description_template", "Mining expansion detected")
        description = desc_template.format(area=zone.area_ha)
        
        return Alert(
            alert_type="excavation_alert",
            title=title,
            description=description,
            location="Active Operations Zone",
            severity=severity,
            geometry=zone.geometry
        )


class WaterAccumulationRule(AlertRule):
    """Alert rule for water accumulation/pooling"""
    
    def evaluate(self, zone: Zone, context: dict[str, Any]) -> Optional[Alert]:
        if not self.enabled or zone.zone_type != "water_accumulation":
            return None
        
        min_area = self.config.get("min_area_ha", 0.05)
        if zone.area_ha < min_area:
            return None
        
        severity = self._get_severity(zone.area_ha)
        if not severity:
            # Default to low severity for water
            severity = "low"
        
        messages = self.config.get("messages", {})
        title = messages.get(severity, f"Water accumulation detected ({zone.area_ha:.1f} ha)")
        title = title.format(area=zone.area_ha)
        
        desc_template = self.config.get("description_template", "Water accumulation detected")
        description = desc_template.format(area=zone.area_ha)
        
        return Alert(
            alert_type="water_warning",
            title=title,
            description=description,
            location="Drainage Area",
            severity=severity,
            geometry=zone.geometry
        )


class BoundaryBreachRule(AlertRule):
    """Alert rule for activity outside approved boundaries"""
    
    def evaluate(self, zone: Zone, context: dict[str, Any]) -> Optional[Alert]:
        if not self.enabled:
            return None
        
        # Get mine boundary from context
        mine_area = context.get("mine_area")
        if not mine_area:
            return None
        
        boundary_geom = mine_area.get("boundary")
        buffer_km = mine_area.get("buffer_km", 2.0)
        
        if not boundary_geom:
            return None
        
        try:
            # Convert to shapely geometries
            from backend.utils.spatial import _extract_geometry
            boundary = shape(_extract_geometry(boundary_geom))
            zone_geom = shape(zone.geometry)
            
            # Create buffer zone (convert km to degrees, approximate)
            # For more accuracy, should reproject to UTM
            buffer_degrees = buffer_km / 111.0  # Rough conversion at equator
            buffered_boundary = boundary.buffer(buffer_degrees)
            
            # Check if zone is outside the buffered boundary
            if not zone_geom.within(buffered_boundary):
                # Zone extends outside approved area
                severity = self.config.get("severity", "high")
                message = self.config.get("message", "Unauthorized activity detected outside lease boundary")
                desc_template = self.config.get(
                    "description_template",
                    "Activity detected outside approved boundary"
                )
                
                return Alert(
                    alert_type="boundary_breach",
                    title=message,
                    description=desc_template,
                    location="Boundary Perimeter",
                    severity=severity,
                    geometry=zone.geometry
                )
        except Exception as e:
            print(f"Error checking boundary breach: {e}")
            return None
        
        return None


class AlertRuleEngine:
    """Manages and executes alert rules"""
    
    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path(__file__).parent / "config" / "alert_rules.json"
        
        self.config_path = config_path
        self.rules: list[AlertRule] = []
        self.load_rules()
    
    def load_rules(self):
        """Load rules from configuration file"""
        if not self.config_path.exists():
            print(f"Warning: Alert rules config not found at {self.config_path}")
            print("Using default rules")
            self._load_default_rules()
            return
        
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        rules_config = config.get("rules", {})
        
        # Initialize rule instances
        self.rules = []
        
        if "vegetation_loss" in rules_config:
            self.rules.append(VegetationLossRule(rules_config["vegetation_loss"]))
        
        if "mining_expansion" in rules_config:
            self.rules.append(MiningExpansionRule(rules_config["mining_expansion"]))
        
        if "water_accumulation" in rules_config:
            self.rules.append(WaterAccumulationRule(rules_config["water_accumulation"]))
        
        if "boundary_breach" in rules_config:
            self.rules.append(BoundaryBreachRule(rules_config["boundary_breach"]))
    
    def _load_default_rules(self):
        """Load hardcoded default rules if config file missing"""
        self.rules = [
            VegetationLossRule({
                "enabled": True,
                "thresholds": {"high": 1.0, "medium": 0.5, "low": 0.2},
                "min_area_ha": 0.2,
                "messages": {
                    "high": "Significant vegetation loss detected ({area:.1f} ha)",
                    "medium": "Moderate vegetation loss detected ({area:.1f} ha)",
                    "low": "Minor vegetation loss detected ({area:.1f} ha)"
                },
                "description_template": "NDVI analysis shows vegetation decline."
            }),
            MiningExpansionRule({
                "enabled": True,
                "thresholds": {"medium": 0.1, "low": 0.05},
                "min_area_ha": 0.05,
                "messages": {
                    "medium": "New excavation surface detected ({area:.1f} ha)",
                    "low": "Small excavation expansion ({area:.1f} ha)"
                },
                "description_template": "Bare Soil Index increase suggests mining expansion."
            }),
            WaterAccumulationRule({
                "enabled": True,
                "thresholds": {"low": 0.05},
                "min_area_ha": 0.05,
                "messages": {
                    "low": "New water pooling detected ({area:.1f} ha)"
                },
                "description_template": "NDWI indicates water accumulation."
            })
        ]
    
    def evaluate_zones(
        self,
        zones: list[Zone],
        context: Optional[dict[str, Any]] = None
    ) -> list[Alert]:
        """
        Evaluate all zones against all rules and generate alerts.
        
        Args:
            zones: List of change detection zones
            context: Additional context (mine_area, etc.)
        
        Returns:
            List of generated alerts
        """
        if context is None:
            context = {}
        
        alerts = []
        
        for zone in zones:
            for rule in self.rules:
                alert = rule.evaluate(zone, context)
                if alert:
                    alerts.append(alert)
        
        return alerts
    
    def get_config(self) -> dict[str, Any]:
        """Get current rule configuration"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {}
    
    def update_config(self, new_config: dict[str, Any]):
        """Update rule configuration and reload"""
        with open(self.config_path, 'w') as f:
            json.dump(new_config, f, indent=2)
        self.load_rules()
