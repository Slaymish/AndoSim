#include "../src/core/types.h"
#include "../src/core/barrier.h"
#include "../src/core/mesh.h"
#include "../src/core/state.h"
#include "../src/core/elasticity.h"
#include "../src/core/stiffness.h"
#include "../src/core/collision.h"
#include <iostream>
#include <cassert>
#include <cmath>

using namespace ando_barrier;

void test_stiffness_contact() {
    std::cout << "Testing contact stiffness..." << std::endl;
    Real mass = 0.1, dt = 0.01, gap = 0.001;
    Vec3 normal(0.0, 0.0, 1.0);
    Mat3 H = Mat3::Identity() * 1000.0;
    Real k = Stiffness::compute_contact_stiffness(mass, dt, gap, normal, H);
    Real expected = mass / (dt * dt) + 1000.0;
    assert(std::abs(k - expected) < 1.0);
    std::cout << "  ✓ Contact stiffness passed" << std::endl;
}

void test_stiffness_pin() {
    std::cout << "Testing pin stiffness..." << std::endl;
    Real mass = 0.1, dt = 0.01;
    Vec3 offset(0.1, 0.0, 0.0);
    Mat3 H = Mat3::Identity() * 500.0;
    Real k = Stiffness::compute_pin_stiffness(mass, dt, offset, H);
    Real expected = mass / (dt * dt) + 500.0;
    assert(std::abs(k - expected) < 1.0);
    std::cout << "  ✓ Pin stiffness passed" << std::endl;
}

void test_stiffness_takeover() {
    std::cout << "Testing stiffness takeover..." << std::endl;
    Real mass = 0.1, dt = 0.01;
    Real gap_large = 0.01, gap_tiny = 1e-5;
    Vec3 normal(0.0, 0.0, 1.0);
    Mat3 H = Mat3::Identity() * 1000.0;
    Real k_large = Stiffness::compute_contact_stiffness(mass, dt, gap_large, normal, H);
    Real k_tiny = Stiffness::compute_contact_stiffness(mass, dt, gap_tiny, normal, H);
    assert(k_tiny > k_large * 10.0);
    std::cout << "  ✓ Stiffness takeover passed" << std::endl;
}

void test_collision_bvh();
void test_collision_point_triangle();
void test_barrier_pin_gradient();
void test_barrier_wall_gradient();

int main() {
    std::cout << "\n========= Stiffness Tests =========\n" << std::endl;
    test_stiffness_contact();
    test_stiffness_pin();
    test_stiffness_takeover();
    
    std::cout << "\n========= Collision Tests =========\n" << std::endl;
    test_collision_bvh();
    test_collision_point_triangle();
    
    std::cout << "\n========= Barrier Gradient Tests =========\n" << std::endl;
    test_barrier_pin_gradient();
    test_barrier_wall_gradient();
    
    std::cout << "\n========= All Tests Passed =========\n" << std::endl;
    return 0;
}

void test_collision_bvh() {
    std::cout << "Testing BVH construction..." << std::endl;
    
    // Create simple mesh: two triangles forming a quad
    std::vector<Vec3> verts = {
        Vec3(0, 0, 0), Vec3(1, 0, 0), Vec3(1, 1, 0), Vec3(0, 1, 0)
    };
    std::vector<Triangle> tris = {
        Triangle(0, 1, 2),
        Triangle(0, 2, 3)
    };
    
    Mesh mesh;
    Material mat;
    mesh.initialize(verts, tris, mat);
    
    State state;
    state.initialize(mesh);
    
    // Build BVH
    std::vector<BVHNode> bvh;
    std::vector<int> indices;
    Collision::build_triangle_bvh(mesh, state, bvh, indices);
    
    assert(!bvh.empty());
    std::cout << "  BVH nodes: " << bvh.size() << std::endl;
    std::cout << "  ✓ BVH construction passed" << std::endl;
}

void test_collision_point_triangle() {
    std::cout << "Testing point-triangle distance..." << std::endl;
    
    // Triangle vertices
    Vec3 a(0, 0, 0);
    Vec3 b(1, 0, 0);
    Vec3 c(0, 1, 0);
    
    // Point above triangle center
    Vec3 p(0.25, 0.25, 0.5);
    
    Real distance;
    Vec3 normal, witness_p, witness_q;
    
    bool result = Collision::narrow_phase_point_triangle(p, a, b, c, 
                                                         distance, normal,
                                                         witness_p, witness_q);
    
    assert(result);
    assert(distance > 0.49 && distance < 0.51);  // Should be ~0.5
    assert(normal[2] > 0.9);  // Normal should point upward (+z)
    
    std::cout << "  Distance: " << distance << std::endl;
    std::cout << "  Normal: " << normal.transpose() << std::endl;
    std::cout << "  ✓ Point-triangle distance passed" << std::endl;
}


void test_barrier_pin_gradient() {
    std::cout << "Testing pin barrier gradient..." << std::endl;
    
    // Create simple state with one vertex
    State state;
    state.positions.push_back(Vec3(1.0, 0.0, 0.0));
    
    Vec3 pin_target(0.0, 0.0, 0.0);
    Real gap = 1.0;  // Distance from target
    Real g_max = 2.0;
    Real k_bar = 1000.0;
    
    // Compute gradient
    VecX gradient = VecX::Zero(3);
    Barrier::compute_pin_gradient(0, pin_target, state, g_max, k_bar, gradient);
    
    // Gradient should point away from target (repulsive force)
    assert(gradient[0] < 0.0);  // Force in -x direction
    assert(std::abs(gradient[1]) < 0.01);
    assert(std::abs(gradient[2]) < 0.01);
    
    std::cout << "  Gradient: " << gradient.transpose() << std::endl;
    std::cout << "  ✓ Pin barrier gradient passed" << std::endl;
}

void test_barrier_wall_gradient() {
    std::cout << "Testing wall barrier gradient..." << std::endl;
    
    // Create state with vertex near wall
    State state;
    state.positions.push_back(Vec3(0.0, 0.0, 0.5));  // 0.5m above wall
    
    Vec3 wall_normal(0.0, 0.0, 1.0);  // Wall at z=0, normal points up
    Real wall_offset = 0.0;
    Real g_max = 1.0;
    Real k_bar = 1000.0;
    
    // Compute gradient
    VecX gradient = VecX::Zero(3);
    Barrier::compute_wall_gradient(0, wall_normal, wall_offset, state, 
                                   g_max, k_bar, gradient);
    
    // Gradient should point upward (away from wall)
    assert(std::abs(gradient[0]) < 0.01);
    assert(std::abs(gradient[1]) < 0.01);
    assert(gradient[2] < 0.0);  // Repulsive force in +z direction
    
    std::cout << "  Gradient: " << gradient.transpose() << std::endl;
    std::cout << "  ✓ Wall barrier gradient passed" << std::endl;
}

