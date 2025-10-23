cmake_minimum_required(VERSION 3.15)

# Test executable for basic functionality
add_executable(test_basic 
    test_basic.cpp
    ${CMAKE_SOURCE_DIR}/src/core/barrier.cpp
    ${CMAKE_SOURCE_DIR}/src/core/mesh.cpp
    ${CMAKE_SOURCE_DIR}/src/core/state.cpp
    ${CMAKE_SOURCE_DIR}/src/core/elasticity.cpp
    ${CMAKE_SOURCE_DIR}/src/core/strain_limiting.cpp
    ${CMAKE_SOURCE_DIR}/src/core/stiffness.cpp
    ${CMAKE_SOURCE_DIR}/src/core/collision.cpp
    ${CMAKE_SOURCE_DIR}/src/core/line_search.cpp
    ${CMAKE_SOURCE_DIR}/src/core/constraints.cpp
    ${CMAKE_SOURCE_DIR}/src/core/pcg_solver.cpp
    ${CMAKE_SOURCE_DIR}/src/core/integrator.cpp
    ${CMAKE_SOURCE_DIR}/src/core/friction.cpp
    ${CMAKE_SOURCE_DIR}/src/core/rigid_body.cpp
    ${CMAKE_SOURCE_DIR}/src/core/matrix_assembly.cpp
)
target_include_directories(test_basic PRIVATE 
    ${CMAKE_SOURCE_DIR}/src/core
    ${EIGEN3_INCLUDE_DIR}
)

# Register test
add_test(NAME BasicTest COMMAND test_basic)

# Test executable for barrier derivative validation
add_executable(test_barrier_derivatives
    test_barrier_derivatives.cpp
    ${CMAKE_SOURCE_DIR}/src/core/barrier.cpp
    ${CMAKE_SOURCE_DIR}/src/core/mesh.cpp
    ${CMAKE_SOURCE_DIR}/src/core/state.cpp
    ${CMAKE_SOURCE_DIR}/src/core/rigid_body.cpp
    ${CMAKE_SOURCE_DIR}/src/core/matrix_assembly.cpp
)
target_include_directories(test_barrier_derivatives PRIVATE
    ${CMAKE_SOURCE_DIR}/src/core
    ${EIGEN3_INCLUDE_DIR}
)

# Register barrier test
add_test(NAME BarrierDerivativesTest COMMAND test_barrier_derivatives)

# Collision validator metrics tests
add_executable(test_collision_validator
    test_collision_validator.cpp
    ${CMAKE_SOURCE_DIR}/src/core/collision_validator.cpp
    ${CMAKE_SOURCE_DIR}/src/core/mesh.cpp
    ${CMAKE_SOURCE_DIR}/src/core/state.cpp
)
target_include_directories(test_collision_validator PRIVATE
    ${CMAKE_SOURCE_DIR}/src/core
    ${EIGEN3_INCLUDE_DIR}
)

add_test(NAME CollisionValidatorTest COMMAND test_collision_validator)

add_executable(test_hybrid
    test_hybrid.cpp
    ${CMAKE_SOURCE_DIR}/src/core/mesh.cpp
    ${CMAKE_SOURCE_DIR}/src/core/state.cpp
    ${CMAKE_SOURCE_DIR}/src/core/constraints.cpp
    ${CMAKE_SOURCE_DIR}/src/core/integrator.cpp
    ${CMAKE_SOURCE_DIR}/src/core/rigid_body.cpp
    ${CMAKE_SOURCE_DIR}/src/core/elasticity.cpp
    ${CMAKE_SOURCE_DIR}/src/core/stiffness.cpp
    ${CMAKE_SOURCE_DIR}/src/core/collision.cpp
    ${CMAKE_SOURCE_DIR}/src/core/line_search.cpp
    ${CMAKE_SOURCE_DIR}/src/core/pcg_solver.cpp
    ${CMAKE_SOURCE_DIR}/src/core/friction.cpp
    ${CMAKE_SOURCE_DIR}/src/core/barrier.cpp
    ${CMAKE_SOURCE_DIR}/src/core/strain_limiting.cpp
    ${CMAKE_SOURCE_DIR}/src/core/matrix_assembly.cpp
)
target_include_directories(test_hybrid PRIVATE
    ${CMAKE_SOURCE_DIR}/src/core
    ${EIGEN3_INCLUDE_DIR}
    /usr/include/eigen3
)

add_test(NAME HybridContactTest COMMAND test_hybrid)
