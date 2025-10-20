# BlenderSim: Ando Barrier Physics

Blender add-on implementing "[A Cubic Barrier with Elasticity-Inclusive Dynamic Stiffness](https://doi.org/10.1145/3687908)" (Ando 2024) for cloth/shell physics simulation.

## Quick Start

**For Blender Users:**
- Start with the [GETTING_STARTED.md](docs/GETTING_STARTED.md) guide for installation and your first viewport simulation.
- See [BLENDER_QUICK_START.md](docs/BLENDER_QUICK_START.md) for detailed panel descriptions, scripted demos, and advanced workflows.

**For Developers:**
- Build: `./build.sh` (requires CMake, Eigen3, pybind11)
- Test: `./build.sh -t` (runs C++ unit tests)
- Demos: `./build/demos/demo_cloth_drape` (standalone C++ demos)
- Visualize: `python3 demos/view_sequence.py output/cloth_drape`


## Build Steps

### 1. Install Dependencies

- Install CMake from https://cmake.org/download/
- Install Eigen3 from https://eigen.tuxfamily.org/
- Install pybind11: `pip install "pybind11[global]"`

### 2. Build the C++ Core Module

From the project root directory:

```bash
# Create build directory
mkdir build
cd build

# Configure with CMake (add pybind11 path if needed)
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=$(python3 -m pybind11 --cmakedir)

# Build
cmake --build . --config Release

# Install to blender_addon directory
cmake --install .
```

**Note for Windows**: Use `python -m pybind11 --cmakedir` instead of `python3`.

### 4. Install Blender Add-on

Once built, the `ando_barrier_core` module will be in the `blender_addon/` directory.

```bash
cp -r blender_addon ~/.config/blender/3.6/scripts/addons/ando_barrier
```

### 5. Enable Add-on in Blender

1. Open Blender
2. Go to Edit → Preferences → Add-ons
3. Search for "Ando Barrier Physics"
4. Enable the checkbox
5. The panel will appear in the 3D View sidebar (press N) under "Ando Physics" tab


## Next Steps

After successful installation:
1. See `demos/` for example scenes (standalone and Blender)
2. Read `docs/BLENDER_QUICK_START.md` for Blender usage guide
3. Check the paper for mathematical details
