# Ando Barrier Physics Engine - Demo Scenes

This directory contains standalone demo executables that showcase the physics engine without requiring Blender.

## Demos

### 1. Cloth Draping (`demo_cloth_drape`)

Demonstrates cloth falling and draping onto a ground plane with pinned corners.

**Features:**
- 1m × 1m cloth mesh (20×20 resolution)
- Two pinned corners (top left and right)
- Ground plane collision at y=0
- Gravity simulation
- Soft cloth material

**Output:** `output/cloth_drape/frame_XXXX.obj`

### 2. Cloth Wall Collision (`demo_cloth_wall`)

Demonstrates cloth being thrown at a wall and falling to the floor.

**Features:**
- 0.5m × 0.5m cloth mesh (15×15 resolution)
- Initial velocity toward wall
- Wall collision at z=0
- Floor collision at y=0
- No pins (free-falling cloth)

**Output:** `output/cloth_wall/frame_XXXX.obj`

## Building

Demos are built automatically with the main project:

```bash
./build.sh
```

Executables will be in `build/demos/`:
- `build/demos/demo_cloth_drape`
- `build/demos/demo_cloth_wall`

## Running

```bash
# Cloth draping demo
./build/demos/demo_cloth_drape

# Cloth wall collision demo
./build/demos/demo_cloth_wall
```

## Visualization

### Quick Preview: Python Viewer

```bash
pip install matplotlib numpy
python demos/view_sequence.py "output/cloth_drape/frame_*.obj"
```

**Controls:** Space/→ (next), ← (prev), Q (quit)

### Blender / MeshLab

Import OBJ sequence or use online viewers like https://3dviewer.net/

## Performance

~5-10 FPS on ARM64 Linux (200-250 frames in 20-50 seconds)

## Customization

Edit demo source files to change mesh resolution, materials, simulation parameters, or gravity.

See `demos/README_cpp.md` for detailed documentation.
