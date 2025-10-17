# Blender Add-on Installation Guide

## Quick Installation

### Option 1: Symlink (Recommended for Development)

```bash
# Find your Blender user scripts directory
# Usually: ~/.config/blender/X.X/scripts/addons/ (Linux)
#          ~/Library/Application Support/Blender/X.X/scripts/addons/ (macOS)
#          %APPDATA%\Blender Foundation\Blender\X.X\scripts\addons\ (Windows)

# For Blender 3.6 on Linux:
ln -s /path/to/BlenderSim/blender_addon ~/.config/blender/3.6/scripts/addons/ando_barrier

# For Blender 4.0 on Linux:
ln -s /path/to/BlenderSim/blender_addon ~/.config/blender/4.0/scripts/addons/ando_barrier
```

### Option 2: Copy Directory

```bash
cp -r /path/to/BlenderSim/blender_addon ~/.config/blender/3.6/scripts/addons/ando_barrier
```

### Option 3: Install ZIP (For Release)

1. Create a ZIP from `blender_addon/`:
   ```bash
   cd /path/to/BlenderSim
   zip -r ando_barrier.zip blender_addon/*
   ```

2. In Blender:
   - Edit → Preferences → Add-ons
   - Click "Install..."
   - Select `ando_barrier.zip`
   - Enable the "Ando Barrier Physics" checkbox

## Enable the Add-on

1. Open Blender
2. Edit → Preferences → Add-ons
3. Search for "Ando"
4. Enable "Ando Barrier Physics" checkbox
5. Check Blender Console (Window → Toggle System Console on Windows, or terminal on Linux/Mac)
6. You should see: `Loaded ando_barrier_core v1.0.0`

## Verify Installation

### Check the Panel

1. Open 3D Viewport
2. Press `N` to show sidebar
3. Look for "Ando Physics" tab
4. You should see:
   - Version info
   - Time Integration settings
   - Newton Solver settings
   - Material Properties
   - Cache & Baking controls

### Quick Test

1. Add a plane: Add → Mesh → Plane
2. Subdivide it: Edit Mode → Right-click → Subdivide (repeat 3-4 times)
3. Tab to Object Mode
4. Open Ando Physics panel (`N` key → Ando Physics tab)
5. Adjust material thickness to 0.001m
6. Click "Bake Simulation"
7. Play animation (Spacebar) to see the cloth fall

## Troubleshooting

### "Core module not loaded" error

**Problem:** The C++ extension isn't being found by Python.

**Solution:**
1. Check that `ando_barrier_core.cpython-*.so` exists in the add-on directory
2. Rebuild the extension:
   ```bash
   cd /path/to/BlenderSim
   ./build.sh
   ```
3. Ensure you're using the correct Python version (check `python3 --version`)
4. Check Blender's Python version: In Blender Console, type `import sys; print(sys.version)`

### "Import error" or "Symbol not found"

**Problem:** The compiled extension doesn't match Blender's Python version.

**Solution:**
1. Check Blender's Python version (usually 3.10 or 3.11)
2. Rebuild with matching Python:
   ```bash
   # Use pyenv to switch Python version if needed
   pyenv install 3.11.7
   pyenv local 3.11.7
   ./build.sh
   ```

### Panel doesn't appear

**Problem:** Add-on not properly registered.

**Solution:**
1. Restart Blender
2. Check Blender Console for errors
3. Manually reload add-on:
   ```python
   # In Blender Python Console
   import bpy
   bpy.ops.wm.addon_disable(module="ando_barrier")
   bpy.ops.wm.addon_enable(module="ando_barrier")
   ```

### Simulation doesn't run

**Problem:** Missing constraints or invalid mesh.

**Checklist:**
- [ ] Mesh is triangulated
- [ ] Mesh has reasonable scale (not too large/small)
- [ ] Ground plane is enabled OR pins are set
- [ ] Time step (dt) is reasonable (1-10 ms)
- [ ] Material properties are set

## System Requirements

- **Blender:** 3.6 or later
- **OS:** Linux (tested), macOS, Windows (untested)
- **Python:** 3.10, 3.11, or 3.13 (must match Blender's Python)
- **Dependencies:** Eigen3, pybind11 (build-time only)

## Directory Structure

```
blender_addon/
├── __init__.py                      # Add-on registration
├── properties.py                    # Scene/material properties
├── operators.py                     # Bake/reset/constraint operators
├── ui.py                           # Panel UI definitions
└── ando_barrier_core.*.so          # Compiled C++ extension
```

## Configuration

All settings are stored per-scene in `bpy.context.scene.ando_barrier`.

### Material Presets (Future)

You can script material presets:

```python
import bpy

props = bpy.context.scene.ando_barrier
mat = props.material_properties

# Rubber
mat.youngs_modulus = 1e6
mat.poisson_ratio = 0.48
mat.density = 1100
mat.thickness = 0.005

# Metal sheet
mat.youngs_modulus = 200e9
mat.poisson_ratio = 0.3
mat.density = 7850
mat.thickness = 0.001
```

## Next Steps

1. ✅ Installation complete
2. Try the Quick Test above
3. Read `BLENDER_GUIDE.md` for detailed usage
4. Check `demos/` for example scenes
5. Report issues on GitHub

## For Developers

### Hot Reload During Development

```python
# In Blender Python Console
import sys
import importlib

# Reload all modules
for mod in list(sys.modules.keys()):
    if 'ando' in mod.lower():
        del sys.modules[mod]

# Re-register
import bpy
bpy.ops.wm.addon_disable(module="ando_barrier")
bpy.ops.wm.addon_enable(module="ando_barrier")
```

### Debug Mode

Add to `__init__.py`:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Build for Distribution

```bash
# Build release
./build.sh -DCMAKE_BUILD_TYPE=Release

# Strip debug symbols
strip blender_addon/ando_barrier_core.*.so

# Create ZIP
zip -r ando_barrier_v1.0.0.zip blender_addon/*
```

## Support

- **Documentation:** `docs/` folder
- **Issues:** GitHub Issues
- **Discussion:** GitHub Discussions
- **Email:** [your email]

---

**Version:** 1.0.0  
**Last Updated:** October 17, 2025
