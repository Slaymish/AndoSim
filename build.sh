#!/bin/bash
# Build script for Ando Barrier Core
# Usage: ./build.sh [options]
#   -d, --debug     Build in debug mode
#   -c, --clean     Clean before build
#   -t, --test      Run tests after build
#   -h, --help      Show this help

set -e  # Exit on error

# Default options
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
        -h|--help)
            echo "Build script for Ando Barrier Core"
            echo "Usage: ./build.sh [options]"
            echo "  -d, --debug     Build in debug mode"
            echo "  -c, --clean     Clean before build"
            echo "  -t, --test      Run tests after build"
            echo "  -h, --help      Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "========================================="
echo "Ando Barrier Core Build Script"
echo "========================================="
echo "Build Type: $BUILD_TYPE"
echo "Project Root: $PROJECT_ROOT"
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
cmake .. \
    -DCMAKE_BUILD_TYPE=$BUILD_TYPE \
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
