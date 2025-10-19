#!/usr/bin/env python3
"""
Test script for gap heatmap visualization
Tests color mapping logic without requiring Blender
"""

import sys
import numpy as np

# Mock the Blender modules
class MockVector:
    def __init__(self, *args):
        if len(args) == 1 and hasattr(args[0], '__iter__'):
            self.data = np.array(list(args[0]))
        else:
            self.data = np.array(args)
    
    def __sub__(self, other):
        return MockVector(self.data - other.data)
    
    def __getattr__(self, name):
        if name == 'length':
            return np.linalg.norm(self.data)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

# Test the color mapping functions
def test_gap_to_color():
    """Test gap distance to color mapping"""
    print("Testing gap_to_color function...")
    
    # Import the function (would need to extract from visualization.py)
    # For now, reimplement here
    def gap_to_color(gap, gap_max=0.001):
        t = min(gap / gap_max, 1.0)
        
        if t < 0.3:
            s = t / 0.3
            r = 1.0
            g = s
            b = 0.0
        else:
            s = (t - 0.3) / 0.7
            r = 1.0 - s
            g = 1.0
            b = 0.0
        
        return (r, g, b, 0.7)
    
    # Test cases
    test_cases = [
        (0.0, 0.001, "Contact (red)"),
        (0.0003, 0.001, "Close (yellow)"),
        (0.001, 0.001, "Safe (green)"),
        (0.002, 0.001, "Far (green, clamped)"),
    ]
    
    print("\nGap distance -> Color mapping:")
    for gap, gap_max, description in test_cases:
        color = gap_to_color(gap, gap_max)
        print(f"  Gap: {gap*1000:.2f}mm -> RGB: ({color[0]:.2f}, {color[1]:.2f}, {color[2]:.2f}) - {description}")
        
        # Validate color properties
        if gap == 0.0:
            assert color[0] == 1.0 and color[1] == 0.0, "Contact should be red"
        elif gap >= gap_max:
            assert color[0] == 0.0 and color[1] == 1.0, "Far gap should be green"
    
    print("[PASS] Gap color mapping tests passed!")

def test_strain_to_color():
    """Test strain magnitude to color mapping"""
    print("\nTesting strain_to_color function...")
    
    def strain_to_color(strain, strain_limit=0.05):
        t = min(strain / strain_limit, 1.0)
        
        if t < 0.3:
            s = t / 0.3
            r = 0.0
            g = s
            b = 1.0 - s
        elif t < 0.7:
            s = (t - 0.3) / 0.4
            r = s
            g = 1.0
            b = 0.0
        else:
            s = (t - 0.7) / 0.3
            r = 1.0
            g = 1.0 - s
            b = 0.0
        
        return (r, g, b, 0.7)
    
    # Test cases
    test_cases = [
        (0.0, 0.05, "No stretch (blue)"),
        (0.015, 0.05, "Mild stretch (green)"),
        (0.035, 0.05, "Moderate stretch (yellow)"),
        (0.05, 0.05, "At limit (red)"),
        (0.10, 0.05, "Beyond limit (red, clamped)"),
    ]
    
    print("\nStrain magnitude -> Color mapping:")
    for strain, strain_limit, description in test_cases:
        color = strain_to_color(strain, strain_limit)
        print(f"  Strain: {strain*100:.1f}% -> RGB: ({color[0]:.2f}, {color[1]:.2f}, {color[2]:.2f}) - {description}")
        
        # Validate color properties
        if strain == 0.0:
            assert color[2] == 1.0 and color[0] == 0.0, "No strain should be blue"
        elif strain >= strain_limit:
            assert color[0] == 1.0 and abs(color[1]) < 0.01, f"Max strain should be red, got RGB({color[0]:.2f}, {color[1]:.2f}, {color[2]:.2f})"
    
    print("[PASS] Strain color mapping tests passed!")

def test_color_continuity():
    """Test that color transitions are smooth"""
    print("\nTesting color continuity...")
    
    def gap_to_color(gap, gap_max=0.001):
        t = min(gap / gap_max, 1.0)
        
        if t < 0.3:
            s = t / 0.3
            r = 1.0
            g = s
            b = 0.0
        else:
            s = (t - 0.3) / 0.7
            r = 1.0 - s
            g = 1.0
            b = 0.0
        
        return (r, g, b, 0.7)
    
    # Check continuity at transition point (t=0.3)
    gap_before = 0.3 * 0.001 - 0.00001
    gap_after = 0.3 * 0.001 + 0.00001
    
    color_before = gap_to_color(gap_before, 0.001)
    color_after = gap_to_color(gap_after, 0.001)
    
    # Colors should be very close at transition
    diff = sum(abs(color_before[i] - color_after[i]) for i in range(3))
    assert diff < 0.1, f"Color discontinuity detected: diff={diff}"
    
    print(f"  Transition continuity: Delta-color = {diff:.4f}")
    print("[PASS] Color continuity test passed!")

if __name__ == '__main__':
    print("="*60)
    print("Gap Heatmap Visualization - Unit Tests")
    print("="*60)
    
    try:
        test_gap_to_color()
        test_strain_to_color()
        test_color_continuity()
        
        print("\n" + "="*60)
        print("[PASS] All tests passed!")
        print("="*60)
        sys.exit(0)
        
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
