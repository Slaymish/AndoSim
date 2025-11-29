cmake_minimum_required(VERSION 3.15)

# Demo executables
include_directories(${CMAKE_SOURCE_DIR}/src/core ${EIGEN3_INCLUDE_DIR})

# Demo 1: Cloth draping onto ground
add_executable(demo_cloth_drape
    demo_cloth_drape.cpp
    ${CMAKE_SOURCE_DIR}/src/core/mesh.cpp
    ${CMAKE_SOURCE_DIR}/src/core/state.cpp
    ${CMAKE_SOURCE_DIR}/src/core/elasticity.cpp
    ${CMAKE_SOURCE_DIR}/src/core/barrier.cpp
    ${CMAKE_SOURCE_DIR}/src/core/stiffness.cpp
    ${CMAKE_SOURCE_DIR}/src/core/strain_limiting.cpp
    ${CMAKE_SOURCE_DIR}/src/core/collision.cpp
    ${CMAKE_SOURCE_DIR}/src/core/line_search.cpp
    ${CMAKE_SOURCE_DIR}/src/core/constraints.cpp
    ${CMAKE_SOURCE_DIR}/src/core/pcg_solver.cpp
    ${CMAKE_SOURCE_DIR}/src/core/integrator.cpp
    ${CMAKE_SOURCE_DIR}/src/core/friction.cpp
    ${CMAKE_SOURCE_DIR}/src/core/rigid_body.cpp
    ${CMAKE_SOURCE_DIR}/src/core/matrix_assembly.cpp
)

target_include_directories(demo_cloth_drape PRIVATE
    ${CMAKE_SOURCE_DIR}/src/core
    ${EIGEN3_INCLUDE_DIR}
)

# Demo 2: Cloth wall collision
add_executable(demo_cloth_wall
    demo_cloth_wall.cpp
    ${CMAKE_SOURCE_DIR}/src/core/mesh.cpp
    ${CMAKE_SOURCE_DIR}/src/core/state.cpp
    ${CMAKE_SOURCE_DIR}/src/core/elasticity.cpp
    ${CMAKE_SOURCE_DIR}/src/core/barrier.cpp
    ${CMAKE_SOURCE_DIR}/src/core/stiffness.cpp
    ${CMAKE_SOURCE_DIR}/src/core/strain_limiting.cpp
    ${CMAKE_SOURCE_DIR}/src/core/collision.cpp
    ${CMAKE_SOURCE_DIR}/src/core/line_search.cpp
    ${CMAKE_SOURCE_DIR}/src/core/constraints.cpp
    ${CMAKE_SOURCE_DIR}/src/core/pcg_solver.cpp
    ${CMAKE_SOURCE_DIR}/src/core/integrator.cpp
    ${CMAKE_SOURCE_DIR}/src/core/friction.cpp
    ${CMAKE_SOURCE_DIR}/src/core/rigid_body.cpp
    ${CMAKE_SOURCE_DIR}/src/core/matrix_assembly.cpp
)

target_include_directories(demo_cloth_wall PRIVATE
    ${CMAKE_SOURCE_DIR}/src/core
    ${EIGEN3_INCLUDE_DIR}
)

# Demo 3: Simple falling test (debugging)
add_executable(demo_simple_fall
    demo_simple_fall.cpp
    ${CMAKE_SOURCE_DIR}/src/core/mesh.cpp
    ${CMAKE_SOURCE_DIR}/src/core/state.cpp
    ${CMAKE_SOURCE_DIR}/src/core/elasticity.cpp
    ${CMAKE_SOURCE_DIR}/src/core/stiffness.cpp
)

target_include_directories(demo_simple_fall PRIVATE
    ${CMAKE_SOURCE_DIR}/src/core
    ${EIGEN3_INCLUDE_DIR}
)
