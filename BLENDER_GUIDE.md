# Blender Integration Guide

## Installation

### 1. Build the C++ Extension

First, build the physics core module:

```bash
cd /path/to/BlenderSim
./build.sh              # Release build
```

This creates `blender_addon/ando_barrier_core.*.so`

### 2. Install Add-on in Blender

**Option A: Symlink (Recommended for Development)**
```bash
ln -s /path/to/BlenderSim/blender_addon ~/.config/blender/3.6/scripts/addons/ando_barrier
```

**Option B: Copy Files**
```bash
cp -r blender_addon ~/.config/blender/3.6/scripts/addons/ando_barrier
```

### 3. Enable the Add-on

1. Open Blender
2. Go to: **Edit → Preferences → Add-ons**
3. Search for: **"Ando"**
4. Enable the checkbox next to **"Ando Barrier Physics"**
5. Verify the version appears (e.g., "ando_barrier_core v1.0.0")

## Quick Start

### Basic Cloth Simulation

1. **Create a Mesh**
   - Add a plane: `Shift+A` → Mesh → Plane
   - Subdivide: Tab (Edit Mode) → Right-click → Subdivide (5-10 times)
   - Tab back to Object Mode

2. **Configure Physics**
   - Open sidebar: `N` key
   - Go to **"Ando Physics"** tab
   - Verify core module loaded (should show version)

3. **Set Up Constraints**
   - **Pin Top Edge**:
     - Tab into Edit Mode
     - Select top edge vertices (Alt+Click edge)
     - In Ando Physics panel → Contact & Constraints → **"Add Pin Constraint"**
     - Tab back to Object Mode
   
   - **Enable Ground**:
     - In Contact & Constraints panel
     - Check **"Enable Ground Plane"**
     - Set **"Ground Height"** to 0.0 (or desired Z position)

4. **Set Material Properties**
   - Expand **"Material Properties"** panel
   - Adjust:
     - **Young's Modulus**: 1e5 (soft cloth) to 1e7 (stiffer)
     - **Density**: 200 kg/m³ (light fabric) to 1000 kg/m³ (heavy)
     - **Thickness**: 0.001 m (1mm typical for cloth)

5. **Configure Simulation**
   - **Time Step (Δt)**: 2.0 ms (default, stable for most cases)
   - **Beta Max**: 0.25 (paper default)
   - **Max Newton Steps**: 8 (increase for more accuracy)

6. **Bake the Simulation**
   - Expand **"Cache & Baking"** panel
   - Set **Cache Start Frame**: 1
   - Set **Cache End Frame**: 250 (or desired length)
   - Click **"Bake Simulation"**
   - Wait for progress (console shows frame updates)

7. **Play Animation**
   - Press `Spacebar` to play cached animation
   - Shape keys store each frame's deformation

### Resetting

To clear cached simulation and start over:
- In Cache & Baking panel → **"Reset Simulation"**
- This removes all shape keys except Basis

## UI Reference

### Main Panel Settings

**Time Integration**
- **Time Step (Δt)**: Timestep in milliseconds (default: 2.0 ms)
  - Smaller = more stable but slower
  - Larger = faster but may destabilize
- **Beta Max**: Maximum β accumulation (default: 0.25, per paper)
  - Don't change unless you understand the paper's integrator

**Newton Solver**
- **Min Newton Steps**: Minimum iterations per timestep (default: 2)
- **Max Newton Steps**: Maximum iterations per timestep (default: 8)
  - Increase for friction or complex contacts

**PCG Solver**
- **PCG Tolerance**: Convergence tolerance (default: 1e-3)
- **PCG Max Iterations**: Maximum linear solver iterations (default: 1000)

### Contact & Constraints Panel

**Contact Parameters**
- **Contact Gap Max (ḡ)**: Maximum gap for barrier activation (default: 0.001 m = 1mm)
  - Should be small relative to mesh size
- **Wall Gap**: Gap threshold for wall collisions (default: 0.001 m)
- **Enable CCD**: Use continuous collision detection (default: ON)
  - Keep enabled to prevent tunneling

**Ground Plane**
- **Enable Ground Plane**: Add infinite ground plane collision
- **Ground Height**: Z-coordinate of ground plane

**Constraint Tools**
- **Add Pin Constraint**: Pins selected vertices in Edit Mode
  - Creates/updates "ando_pins" vertex group
- **Add Wall from Face**: Manual wall constraint dialog (advanced)

### Material Properties Panel

- **Young's Modulus (E)**: Stiffness in Pa
  - Soft cloth: 1e5 (100 kPa)
  - Medium: 1e6 (1 MPa)
  - Stiff fabric: 1e7 (10 MPa)
- **Poisson Ratio (ν)**: Volume preservation (default: 0.3)
  - Range: 0.0 (no lateral contraction) to 0.49 (incompressible)
- **Density (ρ)**: Material density in kg/m³
  - Light fabric: 200 kg/m³
  - Cotton: 500 kg/m³
  - Heavy canvas: 1000 kg/m³
- **Thickness**: Shell thickness in meters (default: 0.001 m = 1mm)

### Friction Panel (Optional)

- **Enable Friction**: Toggle friction forces (default: OFF)
  - Requires more Newton iterations when enabled
- **Friction μ**: Coefficient of friction (default: 0.1)
- **Friction ε**: Friction epsilon smoothing (default: 1e-5 m)

### Strain Limiting Panel (Optional)

- **Enable Strain Limiting**: Prevent excessive stretching (default: OFF)
  - **NOT YET IMPLEMENTED** - placeholder for future feature
- **Strain Limit %**: Maximum allowed strain percentage (default: 5%)

### Cache & Baking Panel

- **Enable Caching**: Store simulation results (default: ON)
- **Cache Start/End Frame**: Frame range to simulate
- **Bake Simulation**: Run physics and store as shape keys
- **Reset Simulation**: Clear all cached shape keys

## Tips and Tricks

### Performance

- **Start small**: Test with 10×10 subdivision before going to 50×50
- **Monitor console**: Frame progress prints to Blender console
- **Expected speeds**:
  - 20×20 mesh (400 vertices): ~90 FPS
  - 50×50 mesh (2500 vertices): ~10-20 FPS
  - 100×100 mesh (10000 vertices): ~2-5 FPS

### Stability

- **Mesh too stiff**: Increase timestep slightly or reduce Young's modulus
- **Cloth exploding**: Decrease timestep or increase Max Newton Steps
- **Penetrations**: Enable CCD (should be on by default)
- **Pins not holding**: Check vertex group weights (should be 1.0)

### Workflow

1. **Model**: Create base mesh, relatively low-poly
2. **Constrain**: Pin vertices, enable ground plane
3. **Test**: Bake 10-20 frames first to verify behavior
4. **Adjust**: Tweak material properties and solver settings
5. **Full bake**: Run complete frame range once satisfied

### Debugging

- **Console output**: `Window → Toggle System Console` (Windows) or run from terminal
- **Shape keys**: Check in Mesh Properties panel after baking
- **Vertex groups**: Verify "ando_pins" group in Object Data Properties
- **Module not loaded**: Rebuild with `./build.sh` and restart Blender

## Limitations (Current Version)

- **No self-collision detection**: Cloth can intersect itself
- **No friction yet**: Friction parameter exists but implementation pending
- **No strain limiting yet**: Feature placeholder only
- **Single object**: Cannot simulate interactions between multiple cloth objects
- **Z-up only**: Blender's coordinate system (Z=up) is hardcoded
- **Triangles required**: Mesh must be triangulated (quads not supported yet)

## Advanced Usage

### Custom Pin Patterns

Pins are controlled by the "ando_pins" vertex group:

1. Enter Edit Mode
2. Select vertices to pin
3. Click "Add Pin Constraint" (creates group if needed)
4. Adjust weights in Object Data Properties → Vertex Groups
5. Weight > 0.5 = pinned, weight ≤ 0.5 = free

### Multiple Walls

Currently only ground plane supported via UI. For custom walls:
- Use Python API or wait for multi-wall UI
- Ground plane normal is fixed to (0, 0, 1) = Z-up

### Parameter Tuning

**For draping cloth**:
- Young's Modulus: 1e5
- Density: 200-500 kg/m³
- Timestep: 2 ms
- Max Newton Steps: 6-8

**For stiff flags/sails**:
- Young's Modulus: 1e6
- Density: 300-800 kg/m³
- Timestep: 1-2 ms
- Max Newton Steps: 8-12

**For tablecloths/heavy fabric**:
- Young's Modulus: 5e5
- Density: 800-1200 kg/m³
- Timestep: 2-3 ms
- Max Newton Steps: 6-8

## Troubleshooting

### "Core module not available"
- **Cause**: C++ extension not built or not in addon directory
- **Fix**: Run `./build.sh` and verify `.so` file in `blender_addon/`

### "No mesh object selected"
- **Cause**: No active object or object is not a mesh
- **Fix**: Select mesh object in outliner

### "Mesh has no triangles"
- **Cause**: Mesh contains only quads/ngons
- **Fix**: Edit Mode → Select All → Face → Triangulate Faces

### Simulation is too slow
- **Cause**: Mesh too dense or too many Newton iterations
- **Fix**: Reduce subdivision, lower Max Newton Steps, or increase timestep slightly

### Cloth explodes immediately
- **Cause**: Timestep too large or material too stiff
- **Fix**: Reduce timestep to 1 ms, reduce Young's modulus, or increase Max Newton Steps

### Pins don't hold
- **Cause**: Pins not properly assigned or vertex group weights incorrect
- **Fix**: Re-add pin constraints in Edit Mode, verify "ando_pins" group exists

### Cloth passes through ground
- **Cause**: CCD disabled, timestep too large, or ground height incorrect
- **Fix**: Enable CCD, reduce timestep, verify ground height matches scene

## Next Steps

- See `demos/` for C++ standalone examples
- Check `PROJECT_STATUS.md` for feature completion status
- Read `.github/copilot-instructions.md` for implementation details
- Contribute: friction and strain limiting features are pending!

## Support

- Issues: GitHub repository
- Documentation: `PROJECT_SPEC.md`, `ROADMAP.md`
- Paper: Ando 2024 "A Cubic Barrier with Elasticity-Inclusive Dynamic Stiffness"
