# Ando Barrier Physics Demos

This directory contains demonstration scripts for the Ando Barrier physics engine.

## 🎬 Showcase Demos (PyVista - Interactive 3D Visualization)

**NEW!** High-quality demos with interactive visualization - no Blender required!

### Quick Start

```bash
# Install PyVista for visualization (optional but recommended)
pip install pyvista

# Run all showcase demos
cd demos
./run_showcase.py all

# Run specific demo
./run_showcase.py flag
./run_showcase.py tablecloth
./run_showcase.py curtains
./run_showcase.py stress

# Export OBJ sequences without visualization
./run_showcase.py --no-viz all
```

### 💾 Cached Simulation Mode

**NEW!** All demos now support `--cached` to skip simulation and load pre-existing OBJ files:

```bash
# Run simulation once (takes time, exports OBJ files)
python demo_flag_wave.py

# Later: Load cached results instantly
python demo_flag_wave.py --cached

# Customize options
python demo_flag_wave.py --frames 600 --output my_test
python demo_flag_wave.py --cached --output my_test
```

**Benefits:**
- ⚡ Instant visualization (no simulation wait)
- 🔄 Re-test visualization parameters without re-simulating
- 📦 Share exact results as OBJ sequences
- 🐛 Debug individual frames in external tools

**Options:**
- `--cached` - Load from OBJ files instead of simulating
- `--frames N` - Number of frames to simulate
- `--output DIR` - OBJ file directory
- `--dt SECONDS` - Timestep (some demos)

See [CACHED_SIMULATION_USAGE.md](../CACHED_SIMULATION_USAGE.md) for full documentation.

### Available Showcase Demos

#### 1. **Waving Flag** (`demo_flag_wave.py`)
- **Scene:** Silk flag pinned on left edge
- **Physics:** Wind forces, pin constraints
- **Mesh:** 40×20 = 800 vertices
- **Duration:** 300 frames (5 seconds @ 60 FPS)
- **Highlights:** Dramatic flowing motion, realistic wrinkles

```bash
./demo_flag_wave.py
```

#### 2. **Tablecloth Pull** (`demo_tablecloth_pull.py`)
- **Scene:** Cotton tablecloth pulled rapidly from table
- **Physics:** Dynamic pulling force, table collision
- **Mesh:** 60×40 = 2400 vertices
- **Duration:** 400 frames
- **Highlights:** Complex wrinkle formation, multi-contact dynamics

```bash
./demo_tablecloth_pull.py
```

#### 3. **Cascading Curtains** (`demo_cascading_curtains.py`)
- **Scene:** Three silk curtain panels at staggered heights
- **Physics:** Multi-layer stacking, self-collision
- **Mesh:** 3 × (25×35) = 2625 vertices
- **Duration:** 500 frames
- **Highlights:** Cloth-on-cloth interaction, draping aesthetics

```bash
./demo_cascading_curtains.py
```

#### 4. **Stress Test** (`demo_stress_test.py`)
- **Scene:** High-resolution cloth drop
- **Physics:** Performance benchmark
- **Mesh:** Configurable (default 50×50 = 2500 vertices)
- **Duration:** 200 frames
- **Highlights:** Tests solver stability and performance limits

```bash
./demo_stress_test.py --resolution 50
./demo_stress_test.py --resolution 80 --frames 100
```

### Interactive Controls

When visualization window opens:
- **Space** - Play/Pause animation
- **Left/Right Arrows** - Step backward/forward
- **Mouse** - Rotate view (left drag), Pan (middle drag), Zoom (scroll)
- **Q** - Quit

### Output

All demos export OBJ sequences to `output/<demo_name>/`:
- `frame_0000.obj`, `frame_0001.obj`, ...
- Compatible with Blender, MeshLab, or any 3D viewer

---

## 🔧 C++ Standalone Demos

These are compiled executables that run without Python:

- **demo_simple_fall** - Basic cloth drop with forward Euler integration
- **demo_cloth_drape** - Full Newton integrator with β accumulation  
- **demo_cloth_wall** - Wall constraint testing

Run from project root:
```bash
./build/demos/demo_simple_fall
./build/demos/demo_cloth_drape
./build/demos/demo_cloth_wall
```

### Python Demos (Legacy Educational)

## Visualization

### Quick Preview: Python Viewer

```bash
pip install matplotlib numpy
python demos/view_sequence.py "output/cloth_drape/frame_*.obj"
```

**Controls:** Space/→ (next), ← (prev), Q (quit)

### Blender / MeshLab

Import OBJ sequence or use online viewers like https://3dviewer.net/

## Installation & Requirements

### Core Requirements
```bash
# Build C++ extension (required)
cd /path/to/BlenderSim
./build.sh

# The extension will be in build/ando_barrier_core.*.so
```

### Optional: PyVista for Interactive Visualization
```bash
# Install PyVista (recommended)
pip install pyvista

# PyVista dependencies (usually auto-installed):
# - vtk
# - numpy
# - scooby
```

### Alternative: Export-Only Mode
If PyVista isn't available, demos will still run and export OBJ sequences:
```bash
./run_showcase.py --no-viz all
```

## Performance Benchmarks

**Hardware:** ARM64 Asahi Linux (Apple Silicon)

| Demo | Vertices | Triangles | Avg Step Time | FPS |
|------|----------|-----------|---------------|-----|
| Flag Wave | 800 | 1,444 | ~7ms | 12 FPS |
| Tablecloth | 2,400 | 4,602 | ~20ms | 4-5 FPS |
| Curtains | 2,625 | 5,046 | ~22ms | 4 FPS |
| Stress 50×50 | 2,500 | 4,802 | ~21ms | 4-5 FPS |
| Stress 80×80 | 6,400 | 12,482 | ~85ms | 1 FPS |

**Note:** Performance scales roughly O(n²) for matrix assembly. Hessian caching (planned) will improve by ~3×.

## Customization

### Material Presets

Edit demos or use framework function:
```python
from demo_framework import create_cloth_material

# Available presets: 'silk', 'cotton', 'leather', 'rubber', 'default'
material = create_cloth_material('silk')
```

### Simulation Parameters

Adjust in demo `setup()` method:
```python
self.params.dt = 0.005              # Timestep (seconds)
self.params.beta_max = 0.25         # β accumulation limit
self.params.max_newton_steps = 10   # Newton iterations
self.params.contact_gap_max = 0.001 # Contact threshold
```

### Mesh Resolution

Change resolution in demo constructors:
```python
# Higher resolution = more detail but slower
resolution_x = 60  # Default varies by demo
resolution_y = 40
```

## Troubleshooting

### "ando_barrier_core not found"
```bash
# Rebuild the extension
cd /path/to/BlenderSim
./build.sh

# Check it exists
ls build/ando_barrier_core.*.so
```

### "PyVista not available"
```bash
# Install PyVista
pip install pyvista

# Or run in export-only mode
./run_showcase.py --no-viz all
```

### Slow Performance
- Reduce mesh resolution in demo files
- Increase `dt` (timestep) for fewer steps per second
- Use `--no-viz` to skip real-time rendering
- Future: Hessian caching will improve performance

### Simulation Instability
- Decrease `dt` for better stability
- Increase `max_newton_steps`
- Decrease `pcg_tol` for more accurate solves
- Check mesh has no degenerate triangles

## See Also

- **C++ Demo Details:** `demos/README_cpp.md`
- **Blender Integration:** `BLENDER_QUICK_START.md`
- **Technical Details:** `PROJECT_STATUS.md`, `DEMO_STATUS.md`
