# Real-Time Simulation Quick Start Guide

## Overview

The Ando Barrier Physics add-on now supports **real-time interactive simulation** directly in the Blender viewport, with optional debug visualization for understanding constraint behavior.

---

## Setup

### 1. Install the Add-on

```bash
# Symlink to Blender addons directory
ln -s /path/to/BlenderSim/blender_addon ~/.config/blender/3.6/scripts/addons/ando_barrier

# Or copy the files
cp -r /path/to/BlenderSim/blender_addon ~/.config/blender/3.6/scripts/addons/ando_barrier
```

### 2. Enable in Blender

1. Edit → Preferences → Add-ons
2. Search: "Ando"
3. Enable checkbox: "Physics: Ando Barrier Physics"
4. Verify version appears in 3D View sidebar

---

## Quick Start: Cloth Drop

### Step 1: Create Mesh
```
Shift+A → Mesh → Plane
Tab (Edit Mode) → Right-click → Subdivide (×5)
```

Result: 20×20 grid (400 vertices)

### Step 2: Add Pin Constraints
```
Edit Mode → Select top row of vertices
N panel → Ando Physics → Contact & Constraints → Add Pin Constraint
```

Result: Blue vertex group "ando_pins" created

### Step 3: Configure Simulation
```
Object Mode → N panel → Ando Physics
Main Panel:
  ├─ dt: 2.0 ms (default)
  ├─ beta_max: 0.25 (default)
  └─ Newton/PCG: defaults OK

Contact & Constraints:
  └─ Enable Ground Plane: ✓
     └─ Height: 0.0

Material Properties:
  └─ Use defaults (cloth-like)
```

### Step 4: Run Real-Time Simulation
```
Real-Time Preview panel:
  1. Click "Initialize" → Wait for confirmation
  2. Click "Play" → Watch cloth fall and drape
  3. ESC to stop, or click "Pause"
```

### Step 5 (Optional): Debug Visualization
```
Debug & Statistics panel:
  1. Click "Show Overlays"
  2. See blue dots at pinned vertices
  3. Monitor FPS in statistics section
```

---

## UI Panels Reference

### Main Panel
- **Time Integration**: dt (timestep), beta_max (β accumulation limit)
- **Newton Solver**: min/max iterations for convergence
- **PCG Solver**: tolerance and max iterations

### Contact & Constraints
- **Contact Parameters**: gap thresholds, CCD toggle
- **Ground Plane**: enable/disable, height adjustment
- **Constraint Operators**: Add pins, add walls

### Material Properties
- **Young's Modulus** (E): Stiffness (default: 1e6 Pa)
- **Poisson Ratio** (ν): Lateral deformation (default: 0.3)
- **Density** (ρ): Mass per volume (default: 1000 kg/m³)
- **Thickness** (h): Shell thickness (default: 0.001 m)

### Real-Time Preview
- **Initialize**: Set up simulation state from mesh
- **Play/Pause**: Continuous playback (24 FPS target)
- **Step**: Advance one frame manually
- **Reset**: Return to initial state
- **Frame Counter**: Current simulation frame

### Debug & Statistics
- **Show/Hide Overlays**: Toggle viewport visualization
- **Legend**:
  - 🔴 Red dots = Contact points
  - 🟢 Green lines = Contact normals
  - 🔵 Blue dots = Pinned vertices
- **Statistics**:
  - Contacts: Active collision count
  - Pins: Constrained vertex count
  - Step time: Per-frame computation (ms)
  - FPS: Frames per second estimate

---

## Controls

### Real-Time Mode

| Action | Control |
|--------|---------|
| Initialize simulation | Click "Initialize" button |
| Start playback | Click "Play" button |
| Stop playback | Press ESC or click "Pause" |
| Single frame | Click "Step" button |
| Reset to start | Click "Reset" button |

### Visualization

| Action | Control |
|--------|---------|
| Toggle overlays | "Show Overlays" / "Hide Overlays" button |
| Adjust view | Standard Blender navigation (MMB, Shift+MMB, Scroll) |

---

## Workflow Comparison

### Traditional Bake Mode
```
1. Set up mesh and constraints
2. Configure parameters
3. Click "Bake Simulation" → Wait minutes
4. Scrub timeline to view result
5. Change parameters → Re-bake from scratch
```

**Use case:** Final animation, high-quality output

### Real-Time Preview Mode
```
1. Set up mesh and constraints
2. Click "Initialize"
3. Click "Play" → Instant feedback
4. Pause, adjust parameters, resume
5. Iterate rapidly
```

**Use case:** Experimentation, learning, tweaking parameters

---

## Tips & Best Practices

### Performance

1. **Start small**: Test with 10×10 grids (100 vertices) before scaling up
2. **Monitor FPS**: Use Debug panel to track performance
3. **Reduce dt**: Smaller timesteps = more accurate but slower
4. **Disable CCD**: Turn off if no fast-moving objects (minor speedup)

### Debugging

1. **Enable overlays early**: Visualize pins to verify setup
2. **Check statistics**: Zero contacts? Check ground plane height
3. **Step-by-step**: Use "Step" button to examine frame-by-frame
4. **Reset often**: "Reset" button restores original geometry

### Common Issues

| Problem | Solution |
|---------|----------|
| Nothing moves | Check gravity is applied (automatic) |
| Falls through floor | Enable ground plane, adjust height |
| Pins not working | Select vertices in Edit Mode before adding |
| Slow performance | Reduce mesh resolution or increase dt |

---

## Parameter Guide

### Quick Presets (Manual for now)

**Rubber** (bouncy, soft):
```
Young's Modulus: 1e5 Pa
Poisson Ratio: 0.45
Density: 900 kg/m³
Thickness: 0.002 m
```

**Metal** (stiff, heavy):
```
Young's Modulus: 2e11 Pa
Poisson Ratio: 0.3
Density: 7850 kg/m³
Thickness: 0.001 m
```

**Cloth** (flexible, light):
```
Young's Modulus: 1e6 Pa
Poisson Ratio: 0.3
Density: 300 kg/m³
Thickness: 0.0005 m
```

**Jelly** (very soft):
```
Young's Modulus: 1e4 Pa
Poisson Ratio: 0.49
Density: 1100 kg/m³
Thickness: 0.003 m
```

---

## Advanced Features

### Friction (Experimental)
```
Friction panel:
  ├─ Enable Friction: ✓
  ├─ mu (μ): 0.3 (coefficient)
  └─ epsilon (ε): 1e-5 (regularization)
```

**Note:** Requires more Newton iterations for stability.

### Strain Limiting (Experimental)
```
Strain Limiting panel:
  ├─ Enable Strain Limiting: ✓
  ├─ Limit: 0.05 (5% max strain)
  └─ tau (τ): 1e-5 (barrier width)
```

**Note:** Prevents over-stretching, useful for cloth.

---

## Keyboard Shortcuts

None currently assigned. Consider adding:
- `Alt+P`: Play/Pause
- `Alt+Shift+P`: Step
- `Alt+R`: Reset
- `Alt+D`: Toggle debug overlays

(Requires Blender keymap customization)

---

## Troubleshooting

### Add-on Not Visible
- Check Preferences → Add-ons → Search "Ando"
- Verify `ando_barrier_core.*.so` exists in addon folder
- Try: Preferences → Add-ons → "Refresh" button

### "Core module not loaded" Error
- Rebuild C++ extension: `./build.sh` in project root
- Check Python version matches Blender's (3.13 for Blender 4.x)
- Verify file permissions on `.so` module

### Simulation Doesn't Initialize
- Select mesh object (not camera/light)
- Mesh must have triangles (use Triangulate modifier if needed)
- Check console (Window → Toggle System Console) for errors

### Slow Performance
- Expected: ~10-15 FPS for 400-vertex mesh (20×20 grid)
- Optimize: Reduce mesh resolution, increase dt
- Future: Hessian caching will improve 3× (planned)

---

## Demo Scenes

### Simple Cloth Drop
```python
import bpy

# Create plane
bpy.ops.mesh.primitive_plane_add(size=2)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.subdivide(number_cuts=9)  # 10×10 grid
bpy.ops.object.mode_set(mode='OBJECT')

# Pin top row
obj = bpy.context.active_object
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='DESELECT')
bpy.ops.object.mode_set(mode='OBJECT')
for v in obj.data.vertices:
    if v.co.z > 0.9:  # Top edge
        v.select = True
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.ando.add_pin_constraint()
bpy.ops.object.mode_set(mode='OBJECT')

# Configure
scene = bpy.context.scene
scene.ando_barrier.enable_ground_plane = True
scene.ando_barrier.ground_plane_height = 0.0
```

Then: Real-Time Preview → Initialize → Play

---

## Next Steps

1. **Experiment**: Try different materials and mesh sizes
2. **Learn**: Enable debug overlays to understand constraints
3. **Create**: Build complex scenes with multiple objects (coming soon)
4. **Optimize**: Monitor FPS, adjust parameters for speed vs. accuracy

**Have questions?** Check `BLENDER_INTEGRATION_PROGRESS.md` for technical details.

**Found a bug?** See project status files for known limitations.

**Want to contribute?** Real-time mode is fully open for extension!
