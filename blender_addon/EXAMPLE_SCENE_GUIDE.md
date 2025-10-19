# Ando Barrier Physics - Example Scene Setup Guide

This guide walks you through creating a complete cloth draping demonstration from scratch in Blender. Follow these steps to set up your first physics simulation with the Ando Barrier add-on.

---

## Prerequisites

1. **Blender 3.6+** installed
2. **Ando Barrier add-on** built and enabled (see `BLENDER_QUICK_START.md`)
3. Verify the add-on is loaded:
   - Open Blender Console (Window → Toggle System Console)
   - You should see: `Loaded ando_barrier_core v1.0.0`

---

## Scene Setup: Cloth Draping Demo

### Step 1: Create the Cloth Mesh

1. **Start with default Blender scene** (delete default cube if present)
2. **Add → Mesh → Plane**
3. **Tab** (Enter Edit Mode)
4. **Right-click → Subdivide** (repeat 5 times for a 17×17 grid)
   - This gives you 289 vertices - good for demonstration
5. **Tab** (Exit Edit Mode)
6. **Scale up the cloth**: Press **S**, then **5**, then **Enter** (makes it 10m × 10m)

### Step 2: Pin the Top Corners

1. **Tab** (Enter Edit Mode)
2. **Alt+A** (Deselect all)
3. **Select top-left corner vertex** (click while holding Shift for multiple selection)
4. **Select top-right corner vertex** (hold Shift + click)
5. Open the **Ando Physics panel** (press **N** key → **Ando Physics** tab)
6. Click **"Add Pin Constraint"** button
7. **Tab** (Exit Edit Mode)
8. You should see: "Added 2 pinned vertices"

### Step 3: Configure Material Preset

In the **Ando Physics** panel:

1. Expand **"Material Properties"** section
2. **Preset dropdown** → Select **"Cloth"**
   - This automatically configures:
     - Young's Modulus: 3.0×10⁵ Pa
     - Poisson Ratio: 0.35
     - Density: 1100 kg/m³
     - Thickness: 0.003 m (3mm)
     - Appropriate timestep and solver settings

### Step 4: Enable Ground Plane

In the **Ando Physics** panel:

1. Expand **"Contact & Constraints"** section
2. Check **"Enable Ground Plane"**
3. Set **"Ground Plane Height"** to **-5.0** (5 meters below origin)

### Step 5: Configure Simulation Settings

Settings should already be good from the "Cloth" preset, but verify:

#### Time Integration (Main Panel):
- **Time Step (Δt)**: 3.0 ms
- **Beta Max**: 0.25

#### Newton Solver:
- **Min Newton Steps**: 2
- **Max Newton Steps**: 8

#### Contact & Constraints:
- **Contact Gap Max (ḡ)**: 0.0005 m (0.5mm)
- **Wall Gap**: 0.0005 m
- **Enable CCD**: ✓ (checked)

#### Friction (expand section):
- **Enable Friction**: ✓
- **Friction μ**: 0.4
- **Friction ε**: 0.00005 m

#### Strain Limiting (expand section):
- **Enable Strain Limiting**: ✓
- **Strain Limit**: 8.0

---

## Running the Simulation

### Option A: Real-Time Preview (Interactive)

1. In **"Real-Time Preview"** section:
   - Click **"Initialize"**
   - You should see confirmation and frame counter
2. Click **"Play"** to run continuously
   - Watch the cloth fall and drape
   - Press **ESC** to pause
3. Use **"Step"** button to advance frame-by-frame
4. Click **"Reset Real-Time"** to restart from initial state

**Enable Debug Visualization:**
1. Expand **"Debug & Statistics"** section
2. Click **"Show Overlays"**
3. You'll see:
   - **Red dots**: Contact points (point-triangle)
   - **Red lines**: Contact normals
   - **Blue dots**: Pinned vertices
   - **Orange dots**: Edge-edge contacts (if any)

### Option B: Baking to Cache (For Animation)

1. In **"Cache & Baking"** section:
   - **Cache Start**: 1
   - **Cache End**: 100 (or however many frames you want)
2. Click **"Bake Simulation"**
   - This will take 30-60 seconds for 100 frames
   - Progress appears in Info panel (bottom of screen)
   - Creates shape keys for each frame
3. **Scrub the timeline** (drag frame indicator) to see animation
4. **Play animation**: Spacebar or Animation → Play

**Baking Statistics:**
- Look for messages like: `✓ Baking complete! 100 frames with 2 pins and 2 pinned vertices`
- Check Console for any warnings or errors

---

## Troubleshooting

### "No 'ando_pins' vertex group found"
- Make sure you selected vertices in **Edit Mode** before clicking "Add Pin Constraint"
- You can manually add to the vertex group:
  - Edit Mode → select vertices
  - Data Properties → Vertex Groups → "ando_pins" → Assign

### "Mesh has no triangles"
- Blender quads need to be triangulated for the solver
- Add Modifier → Triangulate (before simulation)
- Or manually: Edit Mode → Select All → Face → Triangulate Faces

### Cloth falls through ground
- Check ground plane height matches your mesh position
- Increase **Wall Gap** to 0.001 m (1mm) for more safety margin
- Verify **Enable CCD** is checked

### Cloth explodes or looks unstable
- **Reduce time step**: Try 2.0 ms or 1.5 ms
- **Stiffer material**: Try "Metal" preset instead
- **More Newton iterations**: Increase Max Newton Steps to 12
- **Check mesh scale**: Very small meshes (<0.1m) may need different parameters

### Simulation is too slow
- **Reduce mesh density**: Use 3-4 subdivisions instead of 5 (less vertices)
- **Increase time step**: Try 4.0 ms (less stable but faster)
- **Reduce frame count**: Bake 50 frames instead of 100

---

## Understanding the Statistics

In **"Debug & Statistics"** panel (when real-time sim is initialized):

- **Contacts**: Number of active collision constraints (point-triangle, edge-edge, wall)
- **Peak contacts**: Maximum contacts seen during simulation
- **Pins**: Number of pinned vertices (fixed constraints)
- **Step time**: Time per physics timestep in milliseconds
- **FPS**: Physics frames per second (not display FPS)

**Good performance indicators:**
- Step time: 5-15 ms for 17×17 cloth
- FPS: 60-200 (physics, not rendering)
- Contacts: Increases when cloth hits ground (10-50 typical)

**Contact Types:**
- **POINT_TRIANGLE**: Point-vs-triangle collision (most common)
- **EDGE_EDGE**: Edge-vs-edge collision (cloth self-collision or edge contacts)
- **WALL**: Collision with ground plane

---

## Advanced: Multiple Material Presets

Try these variations for different behavior:

### Rubber Sheet (Bouncy)
1. **Preset**: Rubber
2. **Result**: Stiffer, higher friction (μ=0.8), stretchy bounces
3. **Use case**: Elastic membranes, bouncy materials

### Metal Panel (Stiff)
1. **Preset**: Metal
2. **Result**: Very stiff (E=5×10⁸ Pa), minimal deformation, low friction
3. **Use case**: Thin metal sheets, stiff shells

### Jelly Block (Soft)
1. **Preset**: Jelly
2. **Result**: Very soft (E=5×10⁴ Pa), high deformation, high strain limit
3. **Use case**: Soft bodies, gels, highly deformable objects

### Custom Material
1. **Preset**: Custom
2. Manually tune:
   - **Young's Modulus**: Stiffness (10⁴ = jelly, 10⁶ = cloth, 10⁸ = metal)
   - **Poisson Ratio**: Volume preservation (0.3 = compressible, 0.49 = nearly incompressible)
   - **Density**: Mass per volume (water = 1000 kg/m³)
   - **Thickness**: Shell thickness (affects bending stiffness)

---

## Exporting Results

### To Alembic (for other software):
1. After baking, **File → Export → Alembic (.abc)**
2. Check "Apply Modifiers" (includes shape key animation)
3. Use in Maya, Houdini, Cinema 4D, etc.

### To OBJ Sequence:
```python
# Run in Blender Python console after baking
import bpy
obj = bpy.context.active_object
for i, key in enumerate(obj.data.shape_keys.key_blocks):
    if key.name.startswith('frame_'):
        key.value = 1.0
        filepath = f"/tmp/cloth_frame_{i:04d}.obj"
        bpy.ops.export_scene.obj(filepath=filepath, use_selection=True)
        key.value = 0.0
```

---

## Next Steps

1. **Try different mesh shapes**: Sphere, cylinder, custom models
2. **Add multiple objects**: Simulate interactions (requires collision detection)
3. **Experiment with strain limiting**: Increase/decrease to see wrinkle behavior
4. **Profile performance**: Use Debug panel to monitor contacts and step time
5. **Create complex scenes**: Multiple cloths, obstacles, custom constraints

---

## Parameter Reference (Cloth Preset)

| Parameter | Value | Units | Description |
|-----------|-------|-------|-------------|
| Young's Modulus (E) | 3.0×10⁵ | Pa | Stretching stiffness |
| Poisson Ratio (ν) | 0.35 | - | Volume preservation |
| Density (ρ) | 1100 | kg/m³ | Material density |
| Thickness (h) | 0.003 | m | Shell thickness |
| Time Step (Δt) | 3.0 | ms | Integration timestep |
| Beta Max | 0.25 | - | Newton accumulation |
| Contact Gap (ḡ) | 0.5 | mm | Barrier activation distance |
| Friction μ | 0.4 | - | Coulomb friction coefficient |
| Strain Limit | 8.0 | - | Max stretch before limiting |

---

## Support and Feedback

- **Issues**: Check console output and Debug statistics
- **Performance**: Reduce mesh density or increase time step
- **Instability**: Use stiffer material or smaller time step
- **Reference**: See paper "A Cubic Barrier with Elasticity-Inclusive Dynamic Stiffness" (Ando 2024)

Happy simulating! 🎨
