cmake_minimum_required(VERSION 3.17)
project(ando_barrier_core VERSION 1.0.0 LANGUAGES CXX)

# C++ Standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Build options
option(USE_DOUBLE_PRECISION "Use double precision for core computations" OFF)
option(USE_FAST_MATH "Enable fast-math optimizations" OFF)
option(BUILD_TESTS "Build unit tests" ON)

# Compiler flags
if(CMAKE_BUILD_TYPE STREQUAL "Release")
    if(MSVC)
        set(CMAKE_CXX_FLAGS_RELEASE "/O2 /DNDEBUG")
    else()
        set(CMAKE_CXX_FLAGS_RELEASE "-O3")
        if(USE_FAST_MATH)
            set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -ffast-math")
        endif()
    endif()
endif()

# Set default build type
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# Find packages
# Eigen3: accept a CMake package (Ubuntu, Homebrew, vcpkg), an env override,
# or the Windows manual unzip. The include directory must end up set whatever
# route found it, or the bindings fail on Eigen/Core.
find_package(Eigen3 QUIET)
if(Eigen3_FOUND AND NOT EIGEN3_INCLUDE_DIR)
    get_target_property(_eigen_include_dirs Eigen3::Eigen INTERFACE_INCLUDE_DIRECTORIES)
    if(_eigen_include_dirs)
        list(GET _eigen_include_dirs 0 EIGEN3_INCLUDE_DIR)
    endif()
endif()
if(NOT EIGEN3_INCLUDE_DIR AND DEFINED ENV{EIGEN3_INCLUDE_DIR})
    set(EIGEN3_INCLUDE_DIR $ENV{EIGEN3_INCLUDE_DIR})
    message(STATUS "Using Eigen from EIGEN3_INCLUDE_DIR: ${EIGEN3_INCLUDE_DIR}")
endif()
if(NOT EIGEN3_INCLUDE_DIR AND EXISTS "C:/eigen-3.4.0")
    set(EIGEN3_INCLUDE_DIR "C:/eigen-3.4.0")
    message(STATUS "Using Eigen from C:/eigen-3.4.0")
endif()
if(NOT EIGEN3_INCLUDE_DIR)
    message(FATAL_ERROR "Eigen3 not found. Install Eigen3, or set EIGEN3_INCLUDE_DIR to the directory containing Eigen/Core.")
endif()
# Select Python before pybind11 so its module suffix and headers use the
# explicitly requested interpreter rather than legacy FindPythonInterp.
find_package(Python3 COMPONENTS Interpreter Development REQUIRED)
set(PYBIND11_FINDPYTHON ON)
find_package(pybind11 REQUIRED)

# Include directories
include_directories(${EIGEN3_INCLUDE_DIR})
include_directories(${CMAKE_SOURCE_DIR}/src/core)

# Core library sources
set(CORE_SOURCES
    src/core/mesh.cpp
    src/core/state.cpp
    src/core/constraints.cpp
    src/core/elasticity.cpp
    src/core/barrier.cpp
    src/core/stiffness.cpp
    src/core/strain_limiting.cpp
    src/core/collision.cpp
    src/core/line_search.cpp
    src/core/integrator.cpp
    src/core/matrix_assembly.cpp
    src/core/pcg_solver.cpp
    src/core/friction.cpp
    src/core/energy_tracker.cpp
    src/core/collision_validator.cpp
    src/core/adaptive_timestep.cpp
    src/core/rigid_body.cpp
)

# Core library headers
set(CORE_HEADERS
    src/core/mesh.h
    src/core/state.h
    src/core/constraints.h
    src/core/elasticity.h
    src/core/barrier.h
    src/core/stiffness.h
    src/core/strain_limiting.h
    src/core/collision.h
    src/core/line_search.h
    src/core/integrator.h
    src/core/matrix_assembly.h
    src/core/pcg_solver.h
    src/core/friction.h
    src/core/energy_tracker.h
    src/core/collision_validator.h
    src/core/types.h
    src/core/rigid_body.h
)

# Python bindings module
# WITH_SOABI uses FindPython3's suffix, including when a build directory
# still contains cached legacy pybind11 PYTHON_MODULE_EXTENSION values.
pybind11_add_module(ando_barrier_core WITH_SOABI
    src/py/bindings.cpp
    ${CORE_SOURCES}
)

target_include_directories(ando_barrier_core PRIVATE 
    ${CMAKE_SOURCE_DIR}/src/core
    ${EIGEN3_INCLUDE_DIR}
)

# Set precision macro
if(USE_DOUBLE_PRECISION)
    target_compile_definitions(ando_barrier_core PRIVATE USE_DOUBLE_PRECISION)
endif()

# Installation
# Note: On Windows, pybind11 modules are RUNTIME (not LIBRARY), so we specify both
install(TARGETS ando_barrier_core 
    LIBRARY DESTINATION ${CMAKE_SOURCE_DIR}/blender_addon
    RUNTIME DESTINATION ${CMAKE_SOURCE_DIR}/blender_addon
)

# Tests (optional)
if(BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()

# Demos (optional)
option(BUILD_DEMOS "Build demo executables" ON)
if(BUILD_DEMOS)
    add_subdirectory(demos)
endif()
