# Ando Barrier Blender Add-on - Quick Start Guide

## Installation

### 1. Symlink Method (Recommended for Development)

```bash
cd /path/to/BlenderSim
./build.sh  # Build the C++ extension

# For Blender 3.6:
ln -s $(pwd)/blender_addon ~/.config/blender/3.6/scripts/addons/ando_barrier

# For Blender 4.0:
ln -s $(pwd)/blender_addon ~/.config/blender/4.0/scripts/addons/ando_barrier
```

### 2. Enable in Blender

1. Open Blender
2. **Edit → Preferences → Add-ons**
3. Search for **"Ando"**
4. Check the box next to **"Ando Barrier Physics"**
5. You should see in the console: `Loaded ando_barrier_core v1.0.0`

---

## Basic Workflow

### Step 1: Create a Cloth Mesh

1. Add → Mesh → Plane
2. Enter Edit Mode (`Tab`)
3. Right-click → Subdivide (repeat 4-5 times for ~17×17 grid)
4. Exit Edit Mode (`Tab`)

### Step 2: Pin Corners

1. Enter Edit Mode (`Tab`)
2. Select corner vertices (e.g., top two corners)
3. In the **Ando Physics** panel (press `N` → Ando Physics tab):
   - Click **"Add Pin Constraint"**
4. Exit Edit Mode

### Step 3: Configure Materials

In the **Ando Physics** panel:

1. Expand **"Material Properties"**
2. Set thickness: `0.001` (1mm)
3. Adjust stiffness:
   - Soft cloth: Young's modulus = `1e5` to `1e6`
   - Stiff fabric: `1e7` to `1e8`
   - Rubber: `1e6`, Poisson = `0.48`

### Step 4: Set Simulation Parameters

1. **Time Integration:**
   - Time Step: `2.0` to `5.0` ms (smaller = more accurate but slower)
   - Beta Max: `0.25` (default is good)

2. **Contact & Constraints:**
   - Enable Ground Plane: ✓
   - Ground Height: `0.0`

### Step 5: Bake Simulation

1. **Cache & Baking** section:
   - Cache Start: `1`
   - Cache End: `100` (or desired frame count)
2. Click **"Bake Simulation"**
3. Wait for baking to complete (progress in console)

### Step 6: View Animation

1. Press **Spacebar** to play
2. Cloth should drape/fall realistically
3. Scrub timeline to inspect frames

---

## Material Presets

### Soft Cloth
```
Young's Modulus: 5e5 Pa
Poisson Ratio: 0.3
Density: 200 kg/m³
Thickness: 0.001 m
```

### Rubber Sheet
```
Young's Modulus: 1e6 Pa
Poisson Ratio: 0.48
Density: 1100 kg/m³
Thickness: 0.002 m
```

### Stiff Fabric (Canvas)
```
Young's Modulus: 5e7 Pa
Poisson Ratio: 0.3
Density: 500 kg/m³
Thickness: 0.0015 m
```

### Thin Metal Sheet (Aluminum)
```
Young's Modulus: 69e9 Pa
Poisson Ratio: 0.33
Density: 2700 kg/m³
Thickness: 0.0005 m
```

---

## Tips & Tricks

### Performance

- **Mesh Resolution:** Start with 10×10, increase to 20×20 or 30×30 for detail
- **Time Step:** Larger = faster but less stable. 2-5 ms is a good range.
- **Frame Count:** Bake 50-100 frames for quick tests, 250+ for final

### Stability

- If simulation explodes: Reduce time step (e.g., 2 ms → 1 ms)
- If too slow: Reduce mesh resolution or increase time step
- If cloth penetrates ground: Check ground plane is enabled

### Constraints

- **Pins:** Use vertex groups named "ando_pins"
  - Weight > 0.5 = pinned
  - Weight ≤ 0.5 = free
- **Ground:** Automatically applied to all vertices
- **Collisions:** Self-collision handled automatically

### Workflow

1. **Test with low resolution** (10×10) and short duration (50 frames)
2. **Adjust parameters** until behavior looks good
3. **Increase resolution** (20×20 or higher) for final bake
4. **Bake longer sequence** for full animation

---

## Troubleshooting

### "Core module not loaded"

**Problem:** C++ extension not found

**Solution:**
```bash
cd /path/to/BlenderSim
./build.sh
# Check that blender_addon/ando_barrier_core.*.so exists
```

### Simulation doesn't run

**Checklist:**
- [ ] Mesh is triangulated (it auto-triangulates, but check)
- [ ] At least one constraint exists (pins OR ground plane)
- [ ] Material thickness > 0
- [ ] Cache end > cache start

### Cloth falls through ground

**Possible causes:**
- Ground plane disabled → Enable in Contact & Constraints
- Ground height wrong → Set to 0.0 for XY plane
- Time step too large → Reduce to 1-2 ms

### Cloth doesn't move

**Possible causes:**
- All vertices pinned → Check vertex group weights
- Very high stiffness → Reduce Young's modulus
- Beta Max too low → Increase to 0.25
- No gravity → Gravity is automatic, check constraints aren't over-constraining

### Baking is slow

**Expected performance:**
- 10×10 mesh: ~20 FPS (50 frames in 2-3 seconds)
- 20×20 mesh: ~10 FPS (100 frames in 10 seconds)
- 30×30 mesh: ~5 FPS (100 frames in 20 seconds)

**Optimization tips:**
- Use coarser mesh for preview
- Reduce frame count for testing
- Increase time step (within stability limits)

---

## Keyboard Shortcuts

In Blender:

- `N` - Toggle sidebar (where Ando Physics panel is)
- `Tab` - Toggle Edit/Object mode
- `Spacebar` - Play/pause animation
- `Alt+A` - Play animation (older Blender versions)
- `Shift+Left/Right Arrow` - Jump to next/previous keyframe

---

## Advanced Features

### Custom Material via Python

```python
import bpy

props = bpy.context.scene.ando_barrier
mat = props.material_properties

# Custom material
mat.youngs_modulus = 1e7
mat.poisson_ratio = 0.35
mat.density = 800
mat.thickness = 0.002
```

### Multiple Objects

Currently, each object is simulated independently. To simulate multiple objects:
1. Select first object, bake
2. Select second object, bake
3. Repeat for each object

*Future: Multi-object interaction coming in Phase 2*

### Export Simulation Data

Shape keys are stored in the `.blend` file. To export:
1. Select object
2. File → Export → Alembic (.abc) or OBJ Sequence
3. Check "Apply Shape Keys" or "Animation"

---

## API Reference (Python Scripting)

### Run Simulation from Script

```python
import bpy

# Get active object (must be a mesh)
obj = bpy.context.active_object

# Configure
props = bpy.context.scene.ando_barrier
props.cache_start = 1
props.cache_end = 100

# Bake
bpy.ops.ando.bake_simulation()
```

### Reset Simulation

```python
bpy.ops.ando.reset_simulation()
```

### Add Pins Programmatically

```python
import bpy

obj = bpy.context.active_object

# Get or create vertex group
if "ando_pins" not in obj.vertex_groups:
    vg = obj.vertex_groups.new(name="ando_pins")
else:
    vg = obj.vertex_groups["ando_pins"]

# Pin specific vertices (e.g., corners)
corner_indices = [0, 10, 110, 120]  # Example for 11×11 grid
for idx in corner_indices:
    vg.add([idx], 1.0, 'ADD')
```

---

## What's Next?

### Current Features (Phase 1) ✅
- Full physics simulation
- Material properties
- Pin and ground constraints
- Baking to shape keys

### Coming in Phase 2 (Reliability & Visual Feedback) 🚧
- Real-time preview (single-step mode)
- Debug overlays (contact points, forces)
- Collision objects (static obstacles)
- Performance optimization

### Coming in Phase 3 (Advanced Features) 📋
- Friction
- Strain limiting
- Self-collision refinement
- Multi-object interaction
- GPU acceleration (maybe)

---

## Support & Feedback

- **Documentation:** See `docs/` folder
- **Issues:** GitHub Issues
- **Source:** https://github.com/Slaymish/BlenderSim

---

**Version:** 1.0.0  
**Last Updated:** October 17, 2025  
**Blender Compatibility:** 3.6+
