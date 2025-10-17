# BlenderSim: Ando Barrier Physics

Blender add-on implementing "A Cubic Barrier with Elasticity-Inclusive Dynamic Stiffness" (Ando 2024) for cloth/shell physics simulation.

## Quick Start

**For Blender Users:**
- See [BLENDER_GUIDE.md](BLENDER_GUIDE.md) for installation, usage, and tutorials

**For Developers:**
- Build: `./build.sh` (requires CMake, Eigen3, pybind11)
- Test: `./build.sh -t` (runs C++ unit tests)
- Demos: `./build/demos/demo_cloth_drape` (standalone C++ demos)
- Visualize: `python3 demos/view_sequence.py output/cloth_drape`

**Project Status:**
- Core physics engine: ✓ Complete (Tasks 0-9)
- Standalone demos: ✓ Working (90-170 FPS for 200-400 vertex meshes)
- Blender integration: ✓ Mostly Complete (baking functional, overlays pending)
- See [PROJECT_STATUS.md](PROJECT_STATUS.md) and [ROADMAP.md](ROADMAP.md) for details