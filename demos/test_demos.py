#!/usr/bin/env python3
"""
Quick test script to verify all demos work correctly
Runs with reduced frame counts for fast validation
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))

def test_demo(demo_class, demo_name, num_frames=30):
    """Test a single demo"""
    print(f"\nTesting {demo_name}...")
    try:
        demo = demo_class()
        demo.run(num_frames=num_frames)
        print(f"✓ {demo_name} passed ({len(demo.frames)} frames collected)")
        return True
    except Exception as e:
        print(f"✗ {demo_name} failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*60)
    print("BlenderSim Demo Test Suite")
    print("="*60)
    
    results = {}
    
    # Test 1: Flag
    from demo_flag_wave import WavingFlagDemo
    results['flag'] = test_demo(WavingFlagDemo, "Flag Wave Demo", 30)
    
    # Test 2: Tablecloth
    from demo_tablecloth_pull import TableclothPullDemo
    results['tablecloth'] = test_demo(TableclothPullDemo, "Tablecloth Pull Demo", 30)
    
    # Test 3: Curtains
    from demo_cascading_curtains import CascadingCurtainsDemo
    results['curtains'] = test_demo(CascadingCurtainsDemo, "Cascading Curtains Demo", 30)
    
    # Test 4: Stress Test
    from demo_stress_test import StressTestDemo
    demo_stress = StressTestDemo(resolution=15)
    results['stress'] = test_demo(lambda: demo_stress, "Stress Test Demo", 20)
    
    # Summary
    print("\n" + "="*60)
    print("Test Results Summary")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("="*60)
    
    return 0 if passed == total else 1

if __name__ == '__main__':
    sys.exit(main())
