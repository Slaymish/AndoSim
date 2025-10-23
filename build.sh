#!/bin/bash
# Build script for Ando Barrier Core
# Usage: ./build.sh [options]
#   -d, --debug     Build in debug mode
#   -c, --clean     Clean before build
#   -t, --test      Run tests after build
#   -h, --help      Show this help

set -e  # Exit on error

# Default options
PYTHON_EXECUTABLE=""
BUILD_TYPE="Release"
CLEAN=false
RUN_TESTS=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--debug)
            BUILD_TYPE="Debug"
            shift
            ;;
        -c|--clean)
            CLEAN=true
            shift
            ;;
        -t|--test)
            RUN_TESTS=true
            shift
            ;;
        -p|--python)
            if [ -z "${2:-}" ]; then
                echo "Error: --python requires an interpreter path"
                exit 1
            fi
            PYTHON_EXECUTABLE="$2"
            shift 2
            ;;
        -h|--help)
            echo "Build script for Ando Barrier Core"
            echo "Usage: ./build.sh [options]"
            echo "  -d, --debug     Build in debug mode"
            echo "  -c, --clean     Clean before build"
            echo "  -t, --test      Run tests after build"
            echo "  -p, --python    Python interpreter to target (default: auto-detect python3.11)"
            echo "  -h, --help      Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Resolve Python interpreter
if [ -z "$PYTHON_EXECUTABLE" ]; then
    # Try python3 first (more universally available), then python3.11
    for candidate in python3 python3.11; do
        if command -v "$candidate" >/dev/null 2>&1; then
            # Verify it actually works before using it
            if "$candidate" --version >/dev/null 2>&1; then
                PYTHON_EXECUTABLE="$(command -v "$candidate")"
                break
            fi
        fi
    done
fi

if [ -z "$PYTHON_EXECUTABLE" ]; then
    echo "Unable to locate a Python interpreter. Please specify one with --python PATH."
    exit 1
fi

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "========================================="
echo "Ando Barrier Core Build Script"
echo "========================================="
echo "Build Type: $BUILD_TYPE"
echo "Project Root: $PROJECT_ROOT"
echo "Python Executable: $PYTHON_EXECUTABLE"
echo ""

# Clean if requested
if [ "$CLEAN" = true ]; then
    echo "Cleaning previous build..."
    rm -rf build
    rm -f blender_addon/ando_barrier_core*.so
    rm -f blender_addon/ando_barrier_core*.pyd
    echo "Clean complete."
    echo ""
fi

# Create build directory
mkdir -p build
cd build

# Configure
echo "Configuring with CMake..."
PYBIND11_CMAKE_DIR="$("$PYTHON_EXECUTABLE" -m pybind11 --cmakedir)"
cmake .. \
    -DCMAKE_BUILD_TYPE=$BUILD_TYPE \
    -DPython3_EXECUTABLE="$PYTHON_EXECUTABLE" \
    -DCMAKE_PREFIX_PATH="$PYBIND11_CMAKE_DIR" \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON

echo ""
echo "Building..."
cmake --build . --config $BUILD_TYPE -j$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)

echo ""
echo "Installing to blender_addon..."
cmake --install .

echo ""
echo "========================================="
echo "Build Complete!"
echo "========================================="

# Check if module exists
if [ -f "$PROJECT_ROOT/blender_addon/ando_barrier_core"*.so ] || [ -f "$PROJECT_ROOT/blender_addon/ando_barrier_core"*.pyd ]; then
    echo "✓ Module built successfully:"
    ls -lh "$PROJECT_ROOT/blender_addon/ando_barrier_core"*
else
    echo "✗ Warning: Module file not found in blender_addon/"
    exit 1
fi

# Run tests if requested
if [ "$RUN_TESTS" = true ]; then
    echo ""
    echo "Running tests..."
    ctest --output-on-failure
fi

echo ""
echo "Next steps:"
echo "1. Copy or symlink blender_addon/ to Blender's addons directory"
echo "2. Enable 'Ando Barrier Physics' in Blender preferences"
echo "3. Check the BUILD.md for detailed installation instructions"
