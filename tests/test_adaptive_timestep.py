"""
Comprehensive Unit Tests for Adaptive Timestepping
Tests CFL computation, edge cases, and numerical stability
"""

import sys
sys.path.insert(0, 'build')

try:
    import ando_barrier_core as abc
    import numpy as np
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure to build the project first: ./build.sh")
    sys.exit(1)


def create_mesh_from_lists(vertices_list, triangles_list, material):
    """Helper to create mesh from Python lists (converts to proper numpy arrays)."""
    vertices = np.array(vertices_list, dtype=np.float32)
    # Triangles need to be 2D array (n_triangles x 3)
    triangles_flat = np.array(triangles_list, dtype=np.int32)
    n_tris = len(triangles_flat) // 3
    triangles = triangles_flat.reshape(n_tris, 3)
    
    mesh = abc.Mesh()
    mesh.initialize(vertices, triangles, material)
    return mesh


def test_cfl_timestep_basic():
    """Test basic CFL timestep computation"""
    print("\n" + "="*60)
    print("Test: Basic CFL Timestep Computation")
    print("="*60)
    
    # Test case 1: Normal velocity
    max_vel = 1.0  # 1 m/s
    min_edge = 0.01  # 1 cm
    safety = 0.5
    
    dt_cfl = abc.AdaptiveTimestep.compute_cfl_timestep(max_vel, min_edge, safety)
    expected = safety * min_edge / max_vel  # 0.5 * 0.01 / 1.0 = 0.005
    
    print(f"  max_velocity = {max_vel} m/s")
    print(f"  min_edge_length = {min_edge} m")
    print(f"  safety_factor = {safety}")
    print(f"  dt_cfl = {dt_cfl:.6f} s")
    print(f"  expected = {expected:.6f} s")
    
    assert abs(dt_cfl - expected) < 1e-6, f"CFL timestep mismatch: {dt_cfl} vs {expected}"
    print("  [PASS] Basic CFL computation correct")
    
    # Test case 2: High velocity (collision)
    max_vel = 10.0
    dt_cfl = abc.AdaptiveTimestep.compute_cfl_timestep(max_vel, min_edge, safety)
    expected = 0.0005
    
    print(f"\n  High velocity case:")
    print(f"    max_velocity = {max_vel} m/s")
    print(f"    dt_cfl = {dt_cfl:.6f} s (should be smaller)")
    assert dt_cfl < 0.001, "High velocity should give smaller dt"
    print("  [PASS] High velocity handling correct")
    
    # Test case 3: Small velocity (settling)
    max_vel = 0.01
    dt_cfl = abc.AdaptiveTimestep.compute_cfl_timestep(max_vel, min_edge, safety)
    
    print(f"\n  Low velocity case:")
    print(f"    max_velocity = {max_vel} m/s")
    print(f"    dt_cfl = {dt_cfl:.6f} s (should be larger)")
    assert dt_cfl > 0.1, "Low velocity should give larger dt"
    print("  [PASS] Low velocity handling correct")
    
    print("\n[PASS] All basic CFL tests passed!")

def test_cfl_edge_cases():
    """Test CFL computation edge cases"""
    print("\n" + "="*60)
    print("Test: CFL Edge Cases")
    print("="*60)
    
    min_edge = 0.01
    safety = 0.5
    
    # Test case 1: Near-zero velocity (static cloth)
    max_vel = 1e-8
    dt_cfl = abc.AdaptiveTimestep.compute_cfl_timestep(max_vel, min_edge, safety)
    
    print(f"  Near-zero velocity: {max_vel} m/s")
    print(f"    dt_cfl = {dt_cfl:.6f} s")
    assert dt_cfl > 0.0, "dt should be positive even for tiny velocity"
    assert np.isfinite(dt_cfl), "dt should be finite"
    print("  [PASS] Near-zero velocity handled")
    
    # Test case 2: Exact zero velocity (should trigger static detection)
    max_vel = 0.0
    dt_cfl = abc.AdaptiveTimestep.compute_cfl_timestep(max_vel, min_edge, safety)
    
    print(f"\n  Zero velocity: {max_vel} m/s")
    print(f"    dt_cfl = {dt_cfl:.6f} s (should be large for static case)")
    assert np.isfinite(dt_cfl), "dt should be finite for zero velocity"
    print("  [PASS] Zero velocity handled (static detection)")
    
    # Test case 3: Very small edge length
    max_vel = 1.0
    min_edge = 1e-6
    dt_cfl = abc.AdaptiveTimestep.compute_cfl_timestep(max_vel, min_edge, safety)
    expected = safety * min_edge / max_vel
    
    print(f"\n  Tiny edge length: {min_edge} m")
    print(f"    dt_cfl = {dt_cfl:.9f} s")
    print(f"    expected = {expected:.9f} s")
    assert abs(dt_cfl - expected) < 1e-9, "Small edge should give tiny dt"
    print("  [PASS] Tiny edge length handled")
    
    # Test case 4: Different safety factors
    max_vel = 1.0
    min_edge = 0.01
    
    for safety in [0.1, 0.5, 0.9, 1.0]:
        dt_cfl = abc.AdaptiveTimestep.compute_cfl_timestep(max_vel, min_edge, safety)
        expected = safety * min_edge / max_vel
        print(f"\n  Safety factor {safety}:")
        print(f"    dt_cfl = {dt_cfl:.6f} s")
        assert abs(dt_cfl - expected) < 1e-6, f"Safety factor {safety} incorrect"
        print(f"    [PASS] Safety factor {safety} correct")
    
    print("\n[PASS] All edge case tests passed!")

def test_min_edge_length():
    """Test minimum edge length computation on various meshes"""
    print("\n" + "="*60)
    print("Test: Minimum Edge Length Computation")
    print("="*60)
    
    material = abc.Material()
    
    # Test case 1: Simple triangle
    vertices = [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
    ]
    triangles = [0, 1, 2]
    
    mesh = create_mesh_from_lists(vertices, triangles, material)
    
    min_edge = abc.AdaptiveTimestep.compute_min_edge_length(mesh)
    
    print(f"  Simple triangle mesh:")
    print(f"    Vertices: {len(vertices)}")
    print(f"    Triangles: {mesh.num_triangles()}")
    print(f"    Min edge length: {min_edge:.6f} m")
    
    # All edges should be 1.0 or sqrt(2)
    assert 0.99 < min_edge <= 1.01, f"Min edge should be ~1.0, got {min_edge}"
    print("  [PASS] Triangle min edge correct")
    
    # Test case 2: Stretched quad (0.1 x 1.0)
    vertices = [
        [0.0, 0.0, 0.0],
        [0.1, 0.0, 0.0],
        [0.1, 1.0, 0.0],
        [0.0, 1.0, 0.0],
    ]
    triangles = [0, 1, 2, 0, 2, 3]
    
    mesh = create_mesh_from_lists(vertices, triangles, material)
    
    min_edge = abc.AdaptiveTimestep.compute_min_edge_length(mesh)
    
    print(f"\n  Stretched quad (0.1 x 1.0):")
    print(f"    Min edge length: {min_edge:.6f} m")
    assert 0.09 < min_edge < 0.11, f"Min edge should be ~0.1, got {min_edge}"
    print("  [PASS] Stretched quad min edge correct")
    
    # Test case 3: Mixed edge lengths
    vertices = [
        [0.0, 0.0, 0.0],
        [0.01, 0.0, 0.0],  # Very short edge
        [1.0, 0.0, 0.0],   # Long edge
        [0.5, 0.5, 0.0],
    ]
    triangles = [0, 1, 3, 1, 2, 3]
    
    mesh = create_mesh_from_lists(vertices, triangles, material)
    
    min_edge = abc.AdaptiveTimestep.compute_min_edge_length(mesh)
    
    print(f"\n  Mixed edge lengths:")
    print(f"    Min edge length: {min_edge:.6f} m")
    assert 0.009 < min_edge < 0.011, f"Min edge should be ~0.01, got {min_edge}"
    print("  [PASS] Mixed edge lengths min edge correct")
    
    print("\n[PASS] All min edge length tests passed!")

def test_max_velocity():
    """Test maximum velocity computation"""
    print("\n" + "="*60)
    print("Test: Maximum Velocity Computation")
    print("="*60)
    
    # Test case 1: Uniform velocity
    velocities = np.array([1.0, 0.0, 0.0,  # vertex 0
                          1.0, 0.0, 0.0,  # vertex 1
                          1.0, 0.0, 0.0], dtype=np.float32)  # vertex 2
    
    max_vel = abc.AdaptiveTimestep.compute_max_velocity(velocities)
    
    print(f"  Uniform velocity (1, 0, 0):")
    print(f"    max_velocity = {max_vel:.6f} m/s")
    assert abs(max_vel - 1.0) < 1e-6, "Max velocity should be 1.0"
    print("  [PASS] Uniform velocity correct")
    
    # Test case 2: Mixed velocities
    velocities = np.array([0.5, 0.0, 0.0,
                          2.0, 0.0, 0.0,  # Fastest
                          0.1, 0.5, 0.0], dtype=np.float32)
    
    max_vel = abc.AdaptiveTimestep.compute_max_velocity(velocities)
    
    print(f"\n  Mixed velocities:")
    print(f"    max_velocity = {max_vel:.6f} m/s")
    assert abs(max_vel - 2.0) < 1e-6, "Max velocity should be 2.0"
    print("  [PASS] Mixed velocities correct")
    
    # Test case 3: 3D velocity (sqrt(3))
    velocities = np.array([1.0, 1.0, 1.0], dtype=np.float32)
    
    max_vel = abc.AdaptiveTimestep.compute_max_velocity(velocities)
    expected = np.sqrt(3.0)
    
    print(f"\n  3D velocity (1, 1, 1):")
    print(f"    max_velocity = {max_vel:.6f} m/s")
    print(f"    expected = {expected:.6f} m/s")
    assert abs(max_vel - expected) < 1e-5, f"Max velocity should be sqrt(3)"
    print("  [PASS] 3D velocity magnitude correct")
    
    # Test case 4: Zero velocity
    velocities = np.array([0.0, 0.0, 0.0,
                          0.0, 0.0, 0.0], dtype=np.float32)
    
    max_vel = abc.AdaptiveTimestep.compute_max_velocity(velocities)
    
    print(f"\n  Zero velocity:")
    print(f"    max_velocity = {max_vel:.6f} m/s")
    assert max_vel == 0.0, "Max velocity should be 0.0"
    print("  [PASS] Zero velocity correct")
    
    print("\n[PASS] All max velocity tests passed!")

def test_compute_next_dt():
    """Test complete next_dt computation with clamping and smoothing"""
    print("\n" + "="*60)
    print("Test: Complete Next DT Computation")
    print("="*60)
    
    material = abc.Material()
    
    # Create a simple mesh
    vertices = [
        [0.0, 0.0, 0.0],
        [0.01, 0.0, 0.0],
        [0.0, 0.01, 0.0],
    ]
    triangles = [0, 1, 2]
    
    mesh = create_mesh_from_lists(vertices, triangles, material)
    
    # Test case 1: Normal velocity, dt should decrease
    velocities = np.array([1.0, 0.0, 0.0,
                          1.0, 0.0, 0.0,
                          1.0, 0.0, 0.0], dtype=np.float32)
    current_dt = 0.01
    dt_min = 0.001
    dt_max = 0.1
    safety = 0.5
    
    next_dt = abc.AdaptiveTimestep.compute_next_dt(
        velocities, mesh, current_dt, dt_min, dt_max, safety
    )
    
    print(f"  Normal velocity case:")
    print(f"    current_dt = {current_dt:.6f} s")
    print(f"    max_velocity = 1.0 m/s")
    print(f"    min_edge ~= 0.01 m")
    print(f"    next_dt = {next_dt:.6f} s")
    assert dt_min <= next_dt <= dt_max, "dt should be within bounds"
    assert next_dt < current_dt, "dt should decrease for high velocity"
    print("  [PASS] Normal velocity case correct")
    
    # Test case 2: Low velocity, dt should increase (but smoothed)
    velocities = np.array([0.01, 0.0, 0.0,
                          0.01, 0.0, 0.0,
                          0.01, 0.0, 0.0], dtype=np.float32)
    current_dt = 0.001
    
    next_dt = abc.AdaptiveTimestep.compute_next_dt(
        velocities, mesh, current_dt, dt_min, dt_max, safety
    )
    
    print(f"\n  Low velocity case:")
    print(f"    current_dt = {current_dt:.6f} s")
    print(f"    max_velocity = 0.01 m/s")
    print(f"    next_dt = {next_dt:.6f} s")
    assert dt_min <= next_dt <= dt_max, "dt should be within bounds"
    # Should increase but limited by max_increase_ratio (1.5x)
    # Use small epsilon for floating point comparison
    assert next_dt <= current_dt * 1.5 + 1e-9, "dt increase should be smoothed (max 1.5x)"
    print("  [PASS] Low velocity smoothing correct")
    
    # Test case 3: Zero velocity, dt should go to dt_max
    velocities = np.array([0.0, 0.0, 0.0,
                          0.0, 0.0, 0.0,
                          0.0, 0.0, 0.0], dtype=np.float32)
    current_dt = 0.001
    
    next_dt = abc.AdaptiveTimestep.compute_next_dt(
        velocities, mesh, current_dt, dt_min, dt_max, safety
    )
    
    print(f"\n  Zero velocity case:")
    print(f"    current_dt = {current_dt:.6f} s")
    print(f"    max_velocity = 0.0 m/s (static)")
    print(f"    next_dt = {next_dt:.6f} s")
    # Use epsilon for floating point comparison
    assert abs(next_dt - dt_max) < 1e-6, f"dt should go to dt_max for static cloth, got {next_dt}"
    print("  [PASS] Zero velocity (static) handling correct")
    
    # Test case 4: dt clamping at dt_min
    velocities = np.array([100.0, 0.0, 0.0,  # Very high velocity
                          100.0, 0.0, 0.0,
                          100.0, 0.0, 0.0], dtype=np.float32)
    current_dt = 0.01
    dt_min = 0.0001
    dt_max = 0.1
    
    next_dt = abc.AdaptiveTimestep.compute_next_dt(
        velocities, mesh, current_dt, dt_min, dt_max, safety
    )
    
    print(f"\n  Very high velocity case:")
    print(f"    current_dt = {current_dt:.6f} s")
    print(f"    max_velocity = 100.0 m/s")
    print(f"    next_dt = {next_dt:.6f} s")
    # Use epsilon for floating point comparison (allow small underflow)
    assert next_dt >= dt_min - 1e-6, f"dt should not go below dt_min, got {next_dt}"
    print("  [PASS] dt_min clamping correct")
    
    print("\n[PASS] All next_dt computation tests passed!")

def test_numerical_stability():
    """Test numerical stability with extreme values"""
    print("\n" + "="*60)
    print("Test: Numerical Stability (Extreme Values)")
    print("="*60)
    
    # Test case 1: Very large velocity
    max_vel = 1e6
    min_edge = 0.01
    safety = 0.5
    
    dt_cfl = abc.AdaptiveTimestep.compute_cfl_timestep(max_vel, min_edge, safety)
    
    print(f"  Extreme velocity: {max_vel:.1e} m/s")
    print(f"    dt_cfl = {dt_cfl:.9f} s")
    assert np.isfinite(dt_cfl), "dt should be finite for large velocity"
    assert dt_cfl > 0.0, "dt should be positive"
    print("  [PASS] Large velocity stable")
    
    # Test case 2: Very large edge
    max_vel = 1.0
    min_edge = 1e6
    
    dt_cfl = abc.AdaptiveTimestep.compute_cfl_timestep(max_vel, min_edge, safety)
    
    print(f"\n  Extreme edge length: {min_edge:.1e} m")
    print(f"    dt_cfl = {dt_cfl:.3f} s")
    assert np.isfinite(dt_cfl), "dt should be finite for large edge"
    assert dt_cfl > 0.0, "dt should be positive"
    print("  [PASS] Large edge length stable")
    
    # Test case 3: Very small safety factor
    max_vel = 1.0
    min_edge = 0.01
    safety = 1e-6
    
    dt_cfl = abc.AdaptiveTimestep.compute_cfl_timestep(max_vel, min_edge, safety)
    expected = safety * min_edge / max_vel
    
    print(f"\n  Tiny safety factor: {safety:.1e}")
    print(f"    dt_cfl = {dt_cfl:.9f} s")
    assert abs(dt_cfl - expected) < 1e-12, "Tiny safety factor should be accurate"
    print("  [PASS] Tiny safety factor stable")
    
    # Test case 4: Verify no overflow/underflow in velocity computation
    velocities = np.array([1e10, 1e10, 1e10,  # Huge velocity
                          1e-10, 1e-10, 1e-10], dtype=np.float32)  # Tiny velocity
    
    max_vel = abc.AdaptiveTimestep.compute_max_velocity(velocities)
    
    print(f"\n  Mixed extreme velocities:")
    print(f"    max_velocity = {max_vel:.3e} m/s")
    assert np.isfinite(max_vel), "Max velocity should be finite"
    assert max_vel > 1e9, "Should detect huge velocity"
    print("  [PASS] Extreme velocity computation stable")
    
    print("\n[PASS] All numerical stability tests passed!")

def run_all_tests():
    """Run all adaptive timestep unit tests"""
    print("\n" + "="*70)
    print(" " * 15 + "ADAPTIVE TIMESTEP UNIT TEST SUITE")
    print("="*70)
    
    tests = [
        ("Basic CFL Computation", test_cfl_timestep_basic),
        ("CFL Edge Cases", test_cfl_edge_cases),
        ("Min Edge Length", test_min_edge_length),
        ("Max Velocity", test_max_velocity),
        ("Complete Next DT", test_compute_next_dt),
        ("Numerical Stability", test_numerical_stability),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n[FAIL] Test '{name}' FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"\n[FAIL] Test '{name}' ERROR: {e}")
            failed += 1
    
    print("\n" + "="*70)
    print(f"SUMMARY: {passed}/{len(tests)} tests passed")
    if failed > 0:
        print(f"         {failed}/{len(tests)} tests FAILED")
        print("="*70)
        return 1
    else:
        print("         All tests passed! [PASS]")
        print("="*70)
        return 0

if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
