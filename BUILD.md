# Build Instructions for Ando Barrier Core

## Prerequisites

### System Requirements
- **OS**: Linux, macOS, or Windows
- **C++ Compiler**: GCC 7+, Clang 7+, or MSVC 2019+
- **CMake**: 3.15 or later
- **Python**: 3.10 or later (matching your Blender version)
- **Blender**: 3.6 LTS or later

### Dependencies
- **Eigen3**: Linear algebra library (header-only)
- **pybind11**: Python/C++ binding library

## Installation Steps

### 1. Install Dependencies

#### Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install cmake build-essential libeigen3-dev python3-dev
pip3 install pybind11
```

#### macOS (with Homebrew):
```bash
brew install cmake eigen pybind11
```

#### Windows:
- Install CMake from https://cmake.org/download/
- Install Eigen3 from https://eigen.tuxfamily.org/
- Install pybind11: `pip install pybind11`

### 2. Build the C++ Core Module

From the project root directory:

```bash
# Create build directory
mkdir build
cd build

# Configure with CMake
cmake .. -DCMAKE_BUILD_TYPE=Release

# Build
cmake --build . --config Release

# Install to blender_addon directory
cmake --install .
```

### 3. Build Options

You can customize the build with these CMake options:

```bash
# Use double precision (default: OFF for single precision)
cmake .. -DUSE_DOUBLE_PRECISION=ON

# Enable fast-math optimizations (default: OFF)
cmake .. -DUSE_FAST_MATH=ON

# Disable tests (default: ON)
cmake .. -DBUILD_TESTS=OFF
```

### 4. Install Blender Add-on

Once built, the `ando_barrier_core` module will be in the `blender_addon/` directory.

#### Option A: Symlink (Development)
```bash
ln -s /path/to/BlenderSim/blender_addon ~/.config/blender/3.6/scripts/addons/ando_barrier
```

#### Option B: Copy (Deployment)
```bash
cp -r blender_addon ~/.config/blender/3.6/scripts/addons/ando_barrier
```

#### Windows Path:
```
%APPDATA%\Blender Foundation\Blender\3.6\scripts\addons\
```

### 5. Enable Add-on in Blender

1. Open Blender
2. Go to Edit → Preferences → Add-ons
3. Search for "Ando Barrier Physics"
4. Enable the checkbox
5. The panel will appear in the 3D View sidebar (press N) under "Ando Physics" tab

### 6. Verify Installation

Open Blender's Python Console and run:

```python
import sys
sys.path.append('/path/to/BlenderSim/blender_addon')
import ando_barrier_core as abc
print(abc.version())
```

You should see output like: `ando_barrier_core v1.0.0`

## Troubleshooting

### Import Error: "cannot find ando_barrier_core"
- Ensure the build completed successfully
- Check that the `.so` (Linux/Mac) or `.pyd` (Windows) file exists in `blender_addon/`
- Verify Python version matches Blender's Python version

### CMake Cannot Find Eigen3
```bash
# Manually specify Eigen3 path
cmake .. -DEIGEN3_INCLUDE_DIR=/path/to/eigen3
```

### CMake Cannot Find pybind11
```bash
# Ensure pybind11 is installed in Blender's Python
/path/to/blender/3.6/python/bin/python3.10 -m pip install pybind11
```

### Linker Errors
- Ensure you're using a C++17 compatible compiler
- On Linux, you may need to install `libstdc++-dev`

## Development Build

For faster iteration during development:

```bash
cd build
cmake .. -DCMAKE_BUILD_TYPE=Debug
cmake --build .
cmake --install .
```

## Running Tests

If tests are enabled:

```bash
cd build
ctest --output-on-failure
```

## Clean Build

To start fresh:

```bash
rm -rf build
rm -f blender_addon/ando_barrier_core*.so
```

## Next Steps

After successful installation:
1. See `demos/` for example scenes
2. Read the main README for parameter explanations
3. Check the paper for mathematical details
