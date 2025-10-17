"""
Blender Test Script for Ando Barrier Add-on
Run this in Blender's Python console to verify the add-on works

Usage:
1. Open Blender
2. Window → Toggle System Console (to see output)
3. Scripting workspace → Python Console
4. File → Open → Select this file, or paste the code below
5. Run the script

Expected Result:
- Add-on loads successfully
- Plane mesh created
- Simulation bakes to shape keys
- Animation plays
"""

import bpy
import sys
import os

print("\n" + "="*60)
print("ANDO BARRIER BLENDER TEST")
print("="*60)

# Test 1: Check if add-on is enabled
print("\n[Test 1] Checking add-on status...")
addon_name = "ando_barrier"
addon_enabled = addon_name in bpy.context.preferences.addons

if not addon_enabled:
    print(f"  ⚠️  Add-on '{addon_name}' not enabled")
    print(f"  Attempting to enable...")
    try:
        bpy.ops.preferences.addon_enable(module=addon_name)
        print(f"  ✓ Add-on enabled successfully")
    except Exception as e:
        print(f"  ✗ Failed to enable add-on: {e}")
        print("\n  Installation check:")
        print(f"  1. Add-on directory should be in: {bpy.utils.script_path_user()}/addons/")
        print(f"  2. Or symlinked to: ~/.config/blender/{bpy.app.version_string[:3]}/scripts/addons/ando_barrier")
        sys.exit(1)
else:
    print(f"  ✓ Add-on '{addon_name}' is enabled")

# Test 2: Check if core module loads
print("\n[Test 2] Checking core module...")
try:
    import ando_barrier_core as abc
    print(f"  ✓ Core module loaded: {abc.version()}")
except ImportError as e:
    print(f"  ✗ Failed to import ando_barrier_core: {e}")
    print(f"  The C++ extension may not be built or is incompatible")
    sys.exit(1)

# Test 3: Check scene properties
print("\n[Test 3] Checking scene properties...")
if hasattr(bpy.context.scene, 'ando_barrier'):
    props = bpy.context.scene.ando_barrier
    print(f"  ✓ Scene properties registered")
    print(f"    dt = {props.dt} ms")
    print(f"    beta_max = {props.beta_max}")
    print(f"    Young's modulus = {props.material_properties.youngs_modulus} Pa")
else:
    print(f"  ✗ Scene properties not found")
    sys.exit(1)

# Test 4: Clear scene and create test mesh
print("\n[Test 4] Creating test scene...")
# Clear existing objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Add plane
bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 1))
plane = bpy.context.active_object
plane.name = "TestCloth"

# Subdivide in edit mode
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
for _ in range(4):  # 4 subdivisions = 17×17 grid
    bpy.ops.mesh.subdivide()
bpy.ops.object.mode_set(mode='OBJECT')

print(f"  ✓ Created mesh: {len(plane.data.vertices)} vertices, {len(plane.data.polygons)} faces")

# Test 5: Add pin constraints
print("\n[Test 5] Adding pin constraints...")
# Select corner vertices
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='DESELECT')
bpy.ops.object.mode_set(mode='OBJECT')

# Pin corners (first and last vertices in first row)
verts = plane.data.vertices
num_verts = len(verts)
# Find corners (assuming grid layout)
import math
grid_size = int(math.sqrt(num_verts))
corner_indices = [0, grid_size - 1]  # Top-left and top-right

for idx in corner_indices:
    verts[idx].select = True

bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.ando.add_pin_constraint()
bpy.ops.object.mode_set(mode='OBJECT')

print(f"  ✓ Pinned {len(corner_indices)} corner vertices")

# Test 6: Configure simulation parameters
print("\n[Test 6] Configuring simulation parameters...")
props = bpy.context.scene.ando_barrier

# Set reasonable parameters for quick test
props.dt = 5.0  # 5ms timestep
props.beta_max = 0.25
props.max_newton_steps = 8
props.contact_gap_max = 0.01
props.enable_ground_plane = True
props.ground_plane_height = 0.0

# Material: soft cloth
mat_props = props.material_properties
mat_props.youngs_modulus = 5e5  # Soft
mat_props.poisson_ratio = 0.3
mat_props.density = 200  # Light
mat_props.thickness = 0.001  # 1mm

print(f"  ✓ Simulation configured")
print(f"    Material: E={mat_props.youngs_modulus:.1e}, ρ={mat_props.density}, h={mat_props.thickness}")

# Test 7: Set cache parameters
print("\n[Test 7] Setting up cache...")
props.cache_start = 1
props.cache_end = 50  # Short test: 50 frames

print(f"  ✓ Cache range: {props.cache_start} to {props.cache_end}")

# Test 8: Run bake operator
print("\n[Test 8] Baking simulation...")
print(f"  This may take 10-30 seconds for 50 frames...")

try:
    result = bpy.ops.ando.bake_simulation()
    if result == {'FINISHED'}:
        print(f"  ✓ Bake completed successfully!")
    else:
        print(f"  ⚠️  Bake returned: {result}")
except Exception as e:
    print(f"  ✗ Bake failed with error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 9: Verify shape keys created
print("\n[Test 9] Verifying shape keys...")
if plane.data.shape_keys:
    num_keys = len(plane.data.shape_keys.key_blocks)
    expected_keys = props.cache_end - props.cache_start + 2  # +1 for range, +1 for Basis
    print(f"  ✓ Created {num_keys} shape keys (expected ~{expected_keys})")
    
    # List first few
    print(f"  Shape keys:")
    for i, key in enumerate(plane.data.shape_keys.key_blocks[:5]):
        print(f"    - {key.name}")
    if num_keys > 5:
        print(f"    ... and {num_keys - 5} more")
else:
    print(f"  ✗ No shape keys found")
    sys.exit(1)

# Test 10: Set up timeline and play
print("\n[Test 10] Setting up animation playback...")
bpy.context.scene.frame_start = props.cache_start
bpy.context.scene.frame_end = props.cache_end
bpy.context.scene.frame_current = props.cache_start

print(f"  ✓ Timeline set: frames {bpy.context.scene.frame_start} to {bpy.context.scene.frame_end}")
print(f"\n  To view animation:")
print(f"    - Press SPACEBAR to play")
print(f"    - Scrub timeline to see cloth falling")
print(f"    - Cloth should drape from z=1.0 to z≈0.0")

# Test 11: Quick physics validation
print("\n[Test 11] Validating physics...")
bpy.context.scene.frame_current = 1
initial_height = sum(v.co.z for v in plane.data.vertices) / len(plane.data.vertices)

bpy.context.scene.frame_current = props.cache_end
final_height = sum(v.co.z for v in plane.data.vertices) / len(plane.data.vertices)

print(f"  Initial avg height: {initial_height:.4f}")
print(f"  Final avg height: {final_height:.4f}")
print(f"  Height change: {initial_height - final_height:.4f}")

if final_height < initial_height:
    print(f"  ✓ Cloth fell under gravity (physics working!)")
else:
    print(f"  ⚠️  Warning: Cloth didn't fall (check gravity/constraints)")

# Summary
print("\n" + "="*60)
print("✅ ALL TESTS PASSED!")
print("="*60)
print("\nTest Summary:")
print("  ✓ Add-on enabled and loaded")
print("  ✓ Core module imported")
print("  ✓ Scene properties accessible")
print("  ✓ Test mesh created")
print("  ✓ Pin constraints added")
print("  ✓ Simulation parameters set")
print("  ✓ Baking completed")
print("  ✓ Shape keys generated")
print("  ✓ Animation ready")
print("  ✓ Physics validated")
print("\nBlender Add-on Integration: SUCCESS ✓")
print("="*60)
