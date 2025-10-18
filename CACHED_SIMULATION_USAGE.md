# Cached Simulation Feature

## Overview
All Python demos now support loading pre-computed simulations from OBJ sequences, allowing you to:
- Skip expensive simulation re-runs when testing visualization
- Share simulation results without requiring physics computation
- Quickly iterate on visualization parameters

## Usage

### Basic Workflow

**1. Run simulation once (exports OBJ files):**
```bash
python demos/demo_flag_wave.py
```

Output:
- Runs 300 frame simulation
- Exports to `output/flag_wave/frame_0000.obj` through `frame_0300.obj`
- Opens visualization window

**2. Load cached results (instant):**
```bash
python demos/demo_flag_wave.py --cached
```

Output:
- Loads existing OBJ files from `output/flag_wave/`
- Opens visualization window immediately (no simulation)

### Command Line Options

All demos support these arguments:

| Option | Description | Default |
|--------|-------------|---------|
| `--cached` | Load from cached OBJ files | False (run simulation) |
| `--frames N` | Number of frames to simulate | Varies by demo |
| `--output DIR` | Directory for OBJ files | `output/<demo_name>` |
| `--dt SECONDS` | Time step size (cascading_curtains only) | 0.004 |

### Examples

**Run with custom frame count:**
```bash
python demos/demo_flag_wave.py --frames 600
```

**Custom output directory:**
```bash
python demos/demo_flag_wave.py --output my_custom_test
python demos/demo_flag_wave.py --cached --output my_custom_test
```

**Quick test (small simulation):**
```bash
python test_pyvista_fix.py --frames 100
python test_pyvista_fix.py --cached
```

**Cascading curtains with custom timestep:**
```bash
python demos/demo_cascading_curtains.py --frames 1000 --dt 0.002
python demos/demo_cascading_curtains.py --cached
```

## Supported Demos

| Demo | Default Frames | Default Output |
|------|----------------|----------------|
| `demo_flag_wave.py` | 300 | `output/flag_wave` |
| `demo_cascading_curtains.py` | 500 | `output/cascading_curtains` |
| `test_pyvista_fix.py` | 50 | `output/quick_test` |

## Implementation Details

### In PhysicsDemo Base Class

**New method: `load_cached(cache_dir)`**
```python
demo = WavingFlagDemo()
demo.load_cached('output/flag_wave')  # Load from OBJ files
demo.visualize()  # Show visualization
```

Loads all `frame_*.obj` files from the specified directory and populates:
- `demo.frames[]` - List of vertex positions per frame
- `demo.rest_positions` - Initial mesh shape
- `demo.triangles` - Mesh topology

**Helper method: `_load_obj(filepath)`**
Parses a single OBJ file and returns vertices and faces as numpy arrays.

## Error Handling

**Missing cache directory:**
```
FileNotFoundError: Cache directory not found: output/nonexistent
```

**No OBJ files found:**
```
FileNotFoundError: No OBJ files found in output/flag_wave
```

**Solution:** Run the demo without `--cached` first to generate OBJ files.

## Benefits

1. **Fast iteration**: Visualization testing without re-running expensive physics
2. **Reproducibility**: Share exact simulation results as OBJ sequences
3. **Debugging**: Inspect individual frames in external tools (Blender, MeshLab)
4. **Parameter tuning**: Test different FPS, window sizes, camera angles without re-simulating

## Tips

- First run without `--cached` to generate the simulation
- Use `--frames` to adjust simulation length before caching
- OBJ files are portable - can be viewed in any 3D software
- Each frame is ~10-50KB depending on mesh resolution
- 300 frames ≈ 5-15MB total storage
