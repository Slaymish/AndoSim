cmake_minimum_required(VERSION 3.15)

# Test executable for basic functionality
add_executable(test_basic 
    test_basic.cpp
    ${CMAKE_SOURCE_DIR}/src/core/barrier.cpp
    ${CMAKE_SOURCE_DIR}/src/core/mesh.cpp
    ${CMAKE_SOURCE_DIR}/src/core/state.cpp
    ${CMAKE_SOURCE_DIR}/src/core/elasticity.cpp
    ${CMAKE_SOURCE_DIR}/src/core/stiffness.cpp
)
target_include_directories(test_basic PRIVATE 
    ${CMAKE_SOURCE_DIR}/src/core
    ${EIGEN3_INCLUDE_DIR}
)

# Register test
add_test(NAME BasicTest COMMAND test_basic)
