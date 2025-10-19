"""
Ando Barrier Physics - Automatic Example Scene Setup
Run this script in Blender's Text Editor or via command line to automatically
create a cloth draping demonstration scene.

Usage in Blender:
    1. Open Blender
    2. Text Editor → Open → select this file
    3. Click "Run Script" button
    4. Scene will be automatically configured

Usage from command line:
    blender --python create_example_scene.py
"""

import bpy
import bmesh

def setup_example_scene():
    """Create a complete cloth draping example scene"""
    
    # Clear existing scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    print("=" * 60)
    print("Setting up Ando Barrier Example Scene: Cloth Draping")
    print("=" * 60)
    
    # Step 1: Create cloth mesh (plane with subdivisions)
    print("\n[1/6] Creating cloth mesh (17×17 grid)...")
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
    cloth_obj = bpy.context.active_object
    cloth_obj.name = "ClothSimulation"
    
    # Enter edit mode and subdivide
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(cloth_obj.data)
    
    # Subdivide 5 times for 17×17 grid (289 vertices)
    for _ in range(5):
        bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=1, use_grid_fill=True)
    
    bmesh.update_edit_mesh(cloth_obj.data)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Scale up to 10m × 10m
    cloth_obj.scale = (5, 5, 1)
    bpy.ops.object.transform_apply(scale=True)
    
    print(f"   ✓ Created cloth with {len(cloth_obj.data.vertices)} vertices")
    
    # Step 2: Pin top corners
    print("\n[2/6] Adding pin constraints to top corners...")
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Find top corners (max Y, min/max X)
    vertices = cloth_obj.data.vertices
    max_y = max(v.co.y for v in vertices)
    min_x = min(v.co.x for v in vertices)
    max_x = max(v.co.x for v in vertices)
    
    # Select top-left and top-right corners (with small tolerance)
    tolerance = 0.1
    corner_indices = []
    for i, v in enumerate(vertices):
        is_top = abs(v.co.y - max_y) < tolerance
        is_left = abs(v.co.x - min_x) < tolerance
        is_right = abs(v.co.x - max_x) < tolerance
        
        if is_top and (is_left or is_right):
            v.select = True
            corner_indices.append(i)
    
    # Create vertex group for pins
    bpy.ops.object.mode_set(mode='EDIT')
    vg = cloth_obj.vertex_groups.new(name="ando_pins")
    vg.add(corner_indices, 1.0, 'ADD')
    bpy.ops.object.mode_set(mode='OBJECT')
    
    print(f"   ✓ Pinned {len(corner_indices)} corner vertices")
    
    # Step 3: Configure Ando Barrier properties
    print("\n[3/6] Configuring Ando Barrier simulation properties...")
    
    # Check if add-on is enabled
    try:
        props = bpy.context.scene.ando_barrier
    except AttributeError:
        print("   ✗ ERROR: Ando Barrier add-on not enabled!")
        print("   Please enable the add-on in Preferences → Add-ons")
        return False
    
    # Apply Cloth preset
    props.material_preset = "CLOTH"
    print("   ✓ Applied 'Cloth' material preset")
    
    # Enable ground plane
    props.enable_ground_plane = True
    props.ground_plane_height = -5.0
    print("   ✓ Enabled ground plane at Z=-5.0")
    
    # Configure cache settings
    props.cache_start = 1
    props.cache_end = 100
    props.cache_enabled = True
    print("   ✓ Configured cache: frames 1-100")
    
    # Step 4: Add camera
    print("\n[4/6] Setting up camera...")
    bpy.ops.object.camera_add(location=(15, -15, 8))
    camera = bpy.context.active_object
    camera.rotation_euler = (1.1, 0, 0.785)  # Point at cloth
    bpy.context.scene.camera = camera
    print("   ✓ Camera positioned for optimal viewing")
    
    # Step 5: Add lighting
    print("\n[5/6] Setting up lighting...")
    
    # Remove default light if exists
    if "Light" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Light"], do_unlink=True)
    
    # Add sun light
    bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
    sun = bpy.context.active_object
    sun.data.energy = 2.0
    sun.rotation_euler = (0.785, 0, 0.785)
    print("   ✓ Added sun light")
    
    # Step 6: Add ground plane for visual reference
    print("\n[6/6] Adding visual ground plane...")
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, -5.0))
    ground_visual = bpy.context.active_object
    ground_visual.name = "GroundVisual"
    
    # Create simple material for ground
    mat = bpy.data.materials.new(name="GroundMaterial")
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.3, 0.3, 0.3, 1.0)
    ground_visual.data.materials.append(mat)
    print("   ✓ Visual ground plane added")
    
    # Select cloth for user convenience
    bpy.ops.object.select_all(action='DESELECT')
    cloth_obj.select_set(True)
    bpy.context.view_layer.objects.active = cloth_obj
    
    # Print summary
    print("\n" + "=" * 60)
    print("Example Scene Setup Complete!")
    print("=" * 60)
    print("\nScene Summary:")
    print(f"  • Cloth mesh: {len(cloth_obj.data.vertices)} vertices, {len(cloth_obj.data.polygons)} faces")
    print(f"  • Pins: {len(corner_indices)} corner vertices")
    print(f"  • Material: Cloth preset (E=3.0e5 Pa)")
    print(f"  • Ground plane: Z=-5.0")
    print(f"  • Cache: Frames 1-100")
    
    print("\n" + "=" * 60)
    print("Next Steps:")
    print("=" * 60)
    print("1. Open Ando Physics panel (press N → Ando Physics tab)")
    print("2. Real-Time Preview:")
    print("   • Click 'Initialize'")
    print("   • Click 'Play' to run simulation")
    print("   • Click 'Show Overlays' in Debug section to see contacts")
    print("3. OR Baking:")
    print("   • Click 'Bake Simulation' (takes ~30-60 seconds)")
    print("   • Scrub timeline to see animation")
    print("   • Press Spacebar to play animation")
    print("\nFor more details, see EXAMPLE_SCENE_GUIDE.md")
    print("=" * 60)
    
    return True

# Run the setup
if __name__ == "__main__":
    success = setup_example_scene()
    if not success:
        print("\nSetup failed! Check the error messages above.")
