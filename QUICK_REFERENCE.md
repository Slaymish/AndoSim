# Quick Reference: Cached Simulation Mode

## TL;DR

Run simulation once, visualize instantly forever after:

```bash
# First time (slow - runs physics)
python demos/demo_flag_wave.py

# Every time after (fast - loads cache)
python demos/demo_flag_wave.py --cached
```

## Command Reference

### All Demos Support These Flags

| Flag | Description | Example |
|------|-------------|---------|
| `--cached` | Load from OBJ files | `--cached` |
| `--frames N` | Number of frames | `--frames 500` |
| `--output DIR` | Output directory | `--output my_test` |

### Available Demos

| Demo | Default Frames | Default Output | Size |
|------|----------------|----------------|------|
| `test_pyvista_fix.py` | 50 | `output/quick_test` | ~100KB |
| `demo_flag_wave.py` | 300 | `output/flag_wave` | ~20MB |
| `demo_cascading_curtains.py` | 500 | `output/cascading_curtains` | ~50MB |

## Common Workflows

### Quick Test
```bash
python test_pyvista_fix.py         # 50 frames, fast
python test_pyvista_fix.py --cached
```

### Production Run
```bash
python demos/demo_flag_wave.py --frames 600
python demos/demo_flag_wave.py --cached
```

### Multiple Tests
```bash
# Test 1: Default settings
python demos/demo_flag_wave.py --output test1

# Test 2: More frames
python demos/demo_flag_wave.py --frames 500 --output test2

# Compare both
python demos/demo_flag_wave.py --cached --output test1
python demos/demo_flag_wave.py --cached --output test2
```

## PyVista Controls (When Visualization Opens)

| Control | Action |
|---------|--------|
| **Space** | Play/Pause animation |
| **→** | Next frame |
| **←** | Previous frame |
| **Left Mouse Drag** | Orbit camera |
| **Right Mouse Drag** | Pan camera |
| **Scroll Wheel** | Zoom in/out |
| **Q** or **Escape** | Close window |

## Troubleshooting

### "Cache directory not found"
```bash
# Run without --cached first to generate cache
python demos/demo_flag_wave.py
```

### "No OBJ files found"
```bash
# Check output directory
ls output/flag_wave/

# If empty, run simulation
python demos/demo_flag_wave.py
```

### "PyVista not installed"
```bash
pip install pyvista
```

## File Sizes

Typical OBJ file sizes per frame:
- Small mesh (25 verts): ~1KB
- Medium mesh (800 verts): ~65KB
- Large mesh (2625 verts): ~100KB

Cache storage:
- 50 frames × 1KB = 50KB
- 300 frames × 65KB = 20MB
- 500 frames × 100KB = 50MB

## Speed Comparison

| Demo | Simulate | Cached | Speedup |
|------|----------|--------|---------|
| Quick Test | 0.02s | 0.01s | 2× |
| Flag Wave | 26s | 2s | **13×** |
| Curtains | 90s | 3s | **30×** |

## Tips

💡 **Always cache first run** - Don't use `--cached` on first run  
💡 **Use custom output** - Test different parameters without overwriting  
💡 **Check disk space** - Large simulations can use 50-100MB  
💡 **Share results** - OBJ files work in Blender, MeshLab, etc.  
💡 **Debug frames** - Load individual `frame_NNNN.obj` files to inspect issues
