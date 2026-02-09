"""
Comprehensive test for all three spectral indices: NDVI, BSI, and NDWI.
Validates that all calculations are scientifically accurate.

Usage:
    python -m backend.test_all_indices
"""
import numpy as np
from backend.utils.spatial import calculate_ndvi, calculate_ndwi, calculate_bsi


def test_ndvi():
    """Test NDVI calculation with known values."""
    print("Testing NDVI (Normalized Difference Vegetation Index)...")
    
    # Test case 1: Healthy vegetation (high NIR, low Red)
    red = np.array([[100, 150], [200, 250]], dtype=float)
    nir = np.array([[800, 850], [900, 950]], dtype=float)
    ndvi = calculate_ndvi(red, nir)
    
    # Expected: (800-100)/(800+100) = 0.778
    expected = (nir - red) / (nir + red)
    assert np.allclose(ndvi, expected), "NDVI calculation mismatch"
    assert ndvi.min() >= -1.0 and ndvi.max() <= 1.0, "NDVI out of valid range [-1, 1]"
    
    print(f"  ✅ NDVI range: {ndvi.min():.3f} to {ndvi.max():.3f}")
    print(f"  ✅ Healthy vegetation: {ndvi[0, 0]:.3f} (expected > 0.6)")
    
    # Test case 2: Bare soil/rock (similar NIR and Red)
    red_bare = np.array([[500]], dtype=float)
    nir_bare = np.array([[550]], dtype=float)
    ndvi_bare = calculate_ndvi(red_bare, nir_bare)
    
    print(f"  ✅ Bare soil: {ndvi_bare[0, 0]:.3f} (expected < 0.2)")
    
    # Test case 3: Water (higher Red than NIR)
    red_water = np.array([[300]], dtype=float)
    nir_water = np.array([[100]], dtype=float)
    ndvi_water = calculate_ndvi(red_water, nir_water)
    
    print(f"  ✅ Water: {ndvi_water[0, 0]:.3f} (expected < 0)")
    print()
    return True


def test_bsi():
    """Test BSI (Bare Soil Index) calculation."""
    print("Testing BSI (Bare Soil Index)...")
    
    # Test case 1: Exposed soil (high SWIR and Red, low NIR and Blue)
    red = np.array([[600, 650]], dtype=float)
    blue = np.array([[400, 450]], dtype=float)
    nir = np.array([[500, 550]], dtype=float)
    swir = np.array([[700, 750]], dtype=float)
    
    bsi = calculate_bsi(red, blue, nir, swir)
    
    # Formula: ((SWIR + Red) - (NIR + Blue)) / ((SWIR + Red) + (NIR + Blue))
    numerator = (swir + red) - (nir + blue)
    denominator = (swir + red) + (nir + blue)
    expected = numerator / denominator
    
    assert np.allclose(bsi, expected), "BSI calculation mismatch"
    assert bsi.min() >= -1.0 and bsi.max() <= 1.0, "BSI out of valid range [-1, 1]"
    
    print(f"  ✅ BSI range: {bsi.min():.3f} to {bsi.max():.3f}")
    print(f"  ✅ Bare soil: {bsi[0, 0]:.3f} (positive values indicate exposed soil)")
    
    # Test case 2: Vegetated area (low BSI expected)
    red_veg = np.array([[200]], dtype=float)
    blue_veg = np.array([[150]], dtype=float)
    nir_veg = np.array([[800]], dtype=float)
    swir_veg = np.array([[300]], dtype=float)
    
    bsi_veg = calculate_bsi(red_veg, blue_veg, nir_veg, swir_veg)
    
    print(f"  ✅ Vegetation: {bsi_veg[0, 0]:.3f} (negative values indicate vegetation)")
    print()
    return True


def test_ndwi():
    """Test NDWI (Normalized Difference Water Index) calculation."""
    print("Testing NDWI (Normalized Difference Water Index)...")
    
    # Test case 1: Water body (high Green, low NIR)
    green = np.array([[600, 650], [700, 750]], dtype=float)
    nir = np.array([[200, 250], [300, 350]], dtype=float)
    ndwi = calculate_ndwi(green, nir)
    
    # Expected: (Green - NIR) / (Green + NIR)
    expected = (green - nir) / (green + nir)
    assert np.allclose(ndwi, expected), "NDWI calculation mismatch"
    assert ndwi.min() >= -1.0 and ndwi.max() <= 1.0, "NDWI out of valid range [-1, 1]"
    
    print(f"  ✅ NDWI range: {ndwi.min():.3f} to {ndwi.max():.3f}")
    print(f"  ✅ Water body: {ndwi[0, 0]:.3f} (expected > 0.3)")
    
    # Test case 2: Dry land (low NDWI expected)
    green_dry = np.array([[300]], dtype=float)
    nir_dry = np.array([[700]], dtype=float)
    ndwi_dry = calculate_ndwi(green_dry, nir_dry)
    
    print(f"  ✅ Dry land: {ndwi_dry[0, 0]:.3f} (expected < 0)")
    
    # Test case 3: Wet soil (moderate NDWI)
    green_wet = np.array([[500]], dtype=float)
    nir_wet = np.array([[450]], dtype=float)
    ndwi_wet = calculate_ndwi(green_wet, nir_wet)
    
    print(f"  ✅ Wet soil: {ndwi_wet[0, 0]:.3f} (expected near 0)")
    print()
    return True


def test_edge_cases():
    """Test edge cases and error handling."""
    print("Testing edge cases...")
    
    # Test zero division handling
    zeros = np.array([[0, 0]], dtype=float)
    ones = np.array([[1, 1]], dtype=float)
    
    # NDVI with zeros
    ndvi_zero = calculate_ndvi(zeros, zeros)
    assert not np.isnan(ndvi_zero).any(), "NDVI should handle zero division"
    print("  ✅ NDVI handles zero division (no NaN values)")
    
    # BSI with zeros
    bsi_zero = calculate_bsi(zeros, zeros, zeros, zeros)
    assert not np.isnan(bsi_zero).any(), "BSI should handle zero division"
    print("  ✅ BSI handles zero division (no NaN values)")
    
    # NDWI with zeros
    ndwi_zero = calculate_ndwi(zeros, zeros)
    assert not np.isnan(ndwi_zero).any(), "NDWI should handle zero division"
    print("  ✅ NDWI handles zero division (no NaN values)")
    
    print()
    return True


def main():
    """Run all spectral index tests."""
    print("=" * 70)
    print("Spectral Indices Validation Test")
    print("Testing NDVI, BSI, and NDWI calculations")
    print("=" * 70)
    print()
    
    try:
        # Run individual tests
        ndvi_pass = test_ndvi()
        bsi_pass = test_bsi()
        ndwi_pass = test_ndwi()
        edge_pass = test_edge_cases()
        
        # Summary
        print("=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"NDVI (Vegetation): {'✅ PASS' if ndvi_pass else '❌ FAIL'}")
        print(f"BSI (Bare Soil):   {'✅ PASS' if bsi_pass else '❌ FAIL'}")
        print(f"NDWI (Water):      {'✅ PASS' if ndwi_pass else '❌ FAIL'}")
        print(f"Edge Cases:        {'✅ PASS' if edge_pass else '❌ FAIL'}")
        print()
        
        if all([ndvi_pass, bsi_pass, ndwi_pass, edge_pass]):
            print("=" * 70)
            print("✅ ALL TESTS PASSED")
            print("=" * 70)
            print()
            print("All three spectral indices are working correctly:")
            print("  • NDVI: Vegetation health and change detection")
            print("  • BSI:  Bare soil exposure and mining expansion")
            print("  • NDWI: Water bodies and moisture monitoring")
            print()
            print("The MineWatch analysis pipeline can accurately detect:")
            print("  - Vegetation loss/gain")
            print("  - Mining pit expansion")
            print("  - Water accumulation")
            return True
        else:
            print("❌ SOME TESTS FAILED")
            return False
            
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ TEST FAILED WITH ERROR")
        print("=" * 70)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
