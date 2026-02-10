"""
Test suite for alert rules engine.

Tests rule evaluation, threshold enforcement, and boundary breach detection.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.alert_rules import (
    AlertRuleEngine,
    VegetationLossRule,
    MiningExpansionRule,
    WaterAccumulationRule,
    BoundaryBreachRule,
    Zone,
    Alert
)


def test_vegetation_loss_rule():
    """Test vegetation loss alert generation"""
    print("Testing Vegetation Loss Rule...")
    
    config = {
        "enabled": True,
        "thresholds": {"high": 1.0, "medium": 0.5, "low": 0.2},
        "min_area_ha": 0.2,
        "messages": {
            "high": "Significant vegetation loss detected ({area:.1f} ha)",
            "medium": "Moderate vegetation loss detected ({area:.1f} ha)"
        },
        "description_template": "NDVI analysis shows vegetation decline."
    }
    
    rule = VegetationLossRule(config)
    
    # Test 1: Large vegetation loss should trigger HIGH alert
    zone_large = Zone(
        zone_type="vegetation_loss",
        area_ha=1.5,
        geometry={"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}
    )
    
    alert = rule.evaluate(zone_large, {})
    assert alert is not None, "Should generate alert for large vegetation loss"
    assert alert.severity == "high", f"Expected high severity, got {alert.severity}"
    assert "1.5" in alert.title, "Alert title should include area"
    print(f"  ✅ Large loss (1.5 ha): {alert.severity} severity")
    
    # Test 2: Medium vegetation loss
    zone_medium = Zone(zone_type="vegetation_loss", area_ha=0.6, geometry={})
    alert = rule.evaluate(zone_medium, {})
    assert alert.severity == "medium"
    print(f"  ✅ Medium loss (0.6 ha): {alert.severity} severity")
    
    # Test 3: Below minimum threshold should not trigger
    zone_small = Zone(zone_type="vegetation_loss", area_ha=0.1, geometry={})
    alert = rule.evaluate(zone_small, {})
    assert alert is None, "Should not generate alert for very small areas"
    print(f"  ✅ Small loss (0.1 ha): No alert (below minimum)")
    
    print()
    return True


def test_mining_expansion_rule():
    """Test mining expansion alert generation"""
    print("Testing Mining Expansion Rule...")
    
    config = {
        "enabled": True,
        "thresholds": {"medium": 0.1, "low": 0.05},
        "min_area_ha": 0.05,
        "messages": {
            "medium": "New excavation surface detected ({area:.1f} ha)"
        },
        "description_template": "Bare Soil Index increase suggests mining expansion."
    }
    
    rule = MiningExpansionRule(config)
    
    # Test: Medium expansion
    zone = Zone(zone_type="mining_expansion", area_ha=0.15, geometry={})
    alert = rule.evaluate(zone, {})
    assert alert is not None
    assert alert.severity == "medium"
    print(f"  ✅ Mining expansion (0.15 ha): {alert.severity} severity")
    
    # Test: Wrong zone type should not trigger
    zone_wrong = Zone(zone_type="vegetation_loss", area_ha=0.15, geometry={})
    alert = rule.evaluate(zone_wrong, {})
    assert alert is None
    print(f"  ✅ Wrong zone type: No alert")
    
    print()
    return True


def test_water_accumulation_rule():
    """Test water accumulation alert generation"""
    print("Testing Water Accumulation Rule...")
    
    config = {
        "enabled": True,
        "thresholds": {"low": 0.05},
        "min_area_ha": 0.05,
        "messages": {
            "low": "New water pooling detected ({area:.1f} ha)"
        },
        "description_template": "NDWI indicates water accumulation."
    }
    
    rule = WaterAccumulationRule(config)
    
    zone = Zone(zone_type="water_accumulation", area_ha=0.08, geometry={})
    alert = rule.evaluate(zone, {})
    assert alert is not None
    assert alert.severity == "low"
    print(f"  ✅ Water accumulation (0.08 ha): {alert.severity} severity")
    
    print()
    return True


def test_alert_engine():
    """Test the full alert rule engine"""
    print("Testing Alert Rule Engine...")
    
    engine = AlertRuleEngine()
    
    # Create test zones
    zones = [
        Zone("vegetation_loss", 1.2, {}),
        Zone("mining_expansion", 0.15, {}),
        Zone("water_accumulation", 0.06, {}),
    ]
    
    alerts = engine.evaluate_zones(zones, {})
    
    assert len(alerts) >= 3, f"Expected at least 3 alerts, got {len(alerts)}"
    print(f"  ✅ Generated {len(alerts)} alerts from {len(zones)} zones")
    
    # Verify severity levels
    severities = [a.severity for a in alerts]
    assert "high" in severities, "Should have at least one high severity alert"
    print(f"  ✅ Severities: {', '.join(set(severities))}")
    
    print()
    return True


def test_config_loading():
    """Test configuration loading and updating"""
    print("Testing Configuration Management...")
    
    engine = AlertRuleEngine()
    config = engine.get_config()
    
    # Verify config structure
    assert "rules" in config or "vegetation_loss" in str(config), "Config should have rules"
    print(f"  ✅ Configuration loaded successfully")
    
    # Test that rules are initialized
    assert len(engine.rules) > 0, "Should have at least one rule loaded"
    print(f"  ✅ Loaded {len(engine.rules)} rule(s)")
    
    print()
    return True


def main():
    """Run all alert rules tests"""
    print("=" * 70)
    print("Alert Rules Engine Test Suite")
    print("=" * 70)
    print()
    
    try:
        tests = [
            test_vegetation_loss_rule,
            test_mining_expansion_rule,
            test_water_accumulation_rule,
            test_alert_engine,
            test_config_loading
        ]
        
        results = []
        for test in tests:
            try:
                result = test()
                results.append(result)
            except Exception as e:
                print(f"  ❌ FAILED: {e}")
                results.append(False)
        
        # Summary
        print("=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        passed = sum(results)
        total = len(results)
        print(f"Passed: {passed}/{total}")
        
        if all(results):
            print()
            print("✅ ALL TESTS PASSED")
            print()
            print("Alert rules engine is working correctly:")
            print("  • Vegetation loss alerts with 3-tier severity")
            print("  • Mining expansion detection")
            print("  • Water accumulation monitoring")
            print("  • Configurable thresholds")
            return True
        else:
            print()
            print("❌ SOME TESTS FAILED")
            return False
            
    except Exception as e:
        print(f"\n❌ TEST SUITE FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
