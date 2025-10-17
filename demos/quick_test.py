#!/usr/bin/env python3
"""
Quick test script for all demos (no visualization)
Tests physics simulation only - fast validation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))

def test_demo(demo_name, demo_class, frames=10):
    """Test a single demo"""
    print(f"\n{'='*60}")
    print(f"Testing: {demo_name}")
    print(f"{'='*60}")
    
    try:
        demo = demo_class()
        demo.setup()
        
        # Run simulation without visualization
        import time
        start = time.time()
        
        for i in range(frames):
            # Step simulation using the demo's built-in logic
            if hasattr(demo, 'step_simulation'):
                demo.step_simulation()
            else:
                # Manual step for demos without step method
                import numpy as np
                import ando_barrier_core as abc
                
                dt = demo.params.dt
                base_gravity = np.array([0.0, 0.0, -9.81], dtype=np.float32)
                demo.state.apply_gravity(base_gravity, dt)
                abc.Integrator.step(demo.mesh, demo.state, demo.constraints, demo.params)
        
        elapsed = time.time() - start
        fps = frames / elapsed if elapsed > 0 else 0
        
        print(f"✅ PASS: {frames} frames in {elapsed:.2f}s ({fps:.1f} FPS)")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Quick Demo Validation (No Visualization)")
    print("=" * 60)
    
    # Import demo classes
    from demo_flag_wave import WavingFlagDemo
    from demo_tablecloth_pull import TableclothPullDemo
    from demo_cascading_curtains import CascadingCurtainsDemo
    from demo_stress_test import StressTestDemo
    
    # Test each demo
    results = {}
    results['flag'] = test_demo('Flag Wave', WavingFlagDemo, frames=20)
    results['tablecloth'] = test_demo('Tablecloth Pull', TableclothPullDemo, frames=20)
    results['curtains'] = test_demo('Cascading Curtains', CascadingCurtainsDemo, frames=20)
    results['stress'] = test_demo('Stress Test', StressTestDemo, frames=10)
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All demos validated successfully!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total - passed} demo(s) failed")
        sys.exit(1)
