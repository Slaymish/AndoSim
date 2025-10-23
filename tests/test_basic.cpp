#include "../src/core/types.h"
#include "../src/core/barrier.h"
#include "../src/core/mesh.h"
#include "../src/core/state.h"
#include "../src/core/elasticity.h"
#include "../src/core/stiffness.h"
#include "../src/core/collision.h"
#include "../src/core/line_search.h"
#include "../src/core/constraints.h"
#include "../src/core/pcg_solver.h"
#include <iostream>
#include <cassert>
#include <cmath>

using namespace ando_barrier;

constexpr Real kNormalEpsilon = static_cast<Real>(1e-8);

void test_stiffness_contact_point_triangle() {
    std::cout << "Testing point-triangle contact stiffness..." << std::endl;

    State state;
    state.positions = {
        Vec3(0.0, 0.0, 0.2),
        Vec3(0.0, 0.0, 0.0),
        Vec3(1.0, 0.0, 0.0),
        Vec3(0.0, 1.0, 0.0)
    };
    state.masses = {0.1, 0.2, 0.3, 0.4};

    ContactPair contact;
    contact.type = ContactType::POINT_TRIANGLE;
    contact.idx0 = 0;
    contact.idx1 = 1;
    contact.idx2 = 2;
    contact.idx3 = 3;
    contact.normal = Vec3(0.0, 0.0, 1.0);
    contact.witness_q = Vec3(1.0 / 3.0, 1.0 / 3.0, 0.0);
    contact.gap = 0.001;

    const Real dt = 0.01;

    std::vector<Triplet> triplets;
    auto add_diag = [&](Index vertex, Real value) {
        for (int j = 0; j < 3; ++j) {
            triplets.emplace_back(vertex * 3 + j, vertex * 3 + j, value);
        }
    };

    add_diag(0, 900.0);
    add_diag(1, 100.0);
    add_diag(2, 200.0);
    add_diag(3, 300.0);

    SparseMatrix H(12, 12);
    H.setFromTriplets(triplets.begin(), triplets.end());

    Real k = Stiffness::compute_contact_stiffness(contact, state, dt, H);

    Real mass_avg = (state.masses[0] + state.masses[1] + state.masses[2] + state.masses[3]) / Real(4.0);
    Real bary = Real(1.0 / 3.0);
    Real H_diag = Real(900.0) + bary * bary * Real(100.0 + 200.0 + 300.0);
    Real Wn_norm = std::sqrt(Real(1.0) + Real(3.0) * bary * bary);
    Real expected = mass_avg / (dt * dt) + Wn_norm * H_diag;

    assert(std::abs(k - expected) < 1e-3 * expected);
    std::cout << "  ✓ Point-triangle contact stiffness passed" << std::endl;
}

void test_stiffness_pin() {
    std::cout << "Testing pin stiffness..." << std::endl;
    Real mass = 0.1, dt = 0.01;
    Real min_gap = 1e-6;
    Vec3 offset(0.1, 0.0, 0.0);
    Real offset_length = offset.norm();
    Mat3 H = Mat3::Identity() * 500.0;
    Real k = Stiffness::compute_pin_stiffness(mass, dt, offset, H, min_gap);
    Real expected = 500.0 + mass / (offset_length * offset_length);
    assert(std::abs(k - expected) < 1.0);
    std::cout << "  ✓ Pin stiffness passed" << std::endl;
}

void test_stiffness_contact_edge_edge() {
    std::cout << "Testing edge-edge contact stiffness..." << std::endl;

    State state;
    state.positions = {
        Vec3(0.0, 0.0, 0.0),
        Vec3(1.0, 0.0, 0.0),
        Vec3(0.0, 0.1, 0.0),
        Vec3(1.0, 0.1, 0.0)
    };
    state.masses = {0.2, 0.2, 0.2, 0.2};

    ContactPair contact;
    contact.type = ContactType::EDGE_EDGE;
    contact.idx0 = 0;
    contact.idx1 = 1;
    contact.idx2 = 2;
    contact.idx3 = 3;
    contact.normal = Vec3(0.0, 1.0, 0.0);
    contact.gap = 0.001;

    const Real dt = 0.01;

    std::vector<Triplet> triplets;
    auto add_diag = [&](Index vertex, Real value) {
        for (int j = 0; j < 3; ++j) {
            triplets.emplace_back(vertex * 3 + j, vertex * 3 + j, value);
        }
    };

    add_diag(0, 400.0);
    add_diag(1, 500.0);
    add_diag(2, 600.0);
    add_diag(3, 700.0);

    SparseMatrix H(12, 12);
    H.setFromTriplets(triplets.begin(), triplets.end());

    Real k = Stiffness::compute_contact_stiffness(contact, state, dt, H);

    Real mass_avg = Real(0.2);  // All masses identical
    Real H_diag = Real(0.25) * Real(400.0 + 500.0 + 600.0 + 700.0);
    Real expected = mass_avg / (dt * dt) + H_diag;

    assert(std::abs(k - expected) < 1e-5 * expected);
    std::cout << "  ✓ Edge-edge contact stiffness passed" << std::endl;
}

void test_collision_bvh();
void test_collision_point_triangle();
void test_barrier_pin_gradient();
void test_barrier_wall_gradient();
void test_line_search_wall_constraint();
void test_line_search_contact_constraint();
void test_pcg_solver();

int main() {
    std::cout << "\n========= Stiffness Tests =========\n" << std::endl;
    test_stiffness_contact_point_triangle();
    test_stiffness_pin();
    test_stiffness_contact_edge_edge();
    
    std::cout << "\n========= Collision Tests =========\n" << std::endl;
    test_collision_bvh();
    test_collision_point_triangle();
    
    std::cout << "\n========= Barrier Gradient Tests =========\n" << std::endl;
    test_barrier_pin_gradient();
    test_barrier_wall_gradient();
    
    std::cout << "\n========= Line Search Tests =========\n" << std::endl;
    test_line_search_wall_constraint();
    test_line_search_contact_constraint();
    
    std::cout << "\n========= Solver Tests =========\n" << std::endl;
    test_pcg_solver();
    
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
    Barrier::compute_pin_gradient(0, pin_target, state, g_max, k_bar,
                                  kNormalEpsilon, gradient);
    
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
                                   g_max, k_bar, kNormalEpsilon, gradient);
    
    // Gradient should point upward (away from wall)
    assert(std::abs(gradient[0]) < 0.01);
    assert(std::abs(gradient[1]) < 0.01);
    assert(gradient[2] < 0.0);  // Repulsive force in +z direction
    
    std::cout << "  Gradient: " << gradient.transpose() << std::endl;
    std::cout << "  ✓ Wall barrier gradient passed" << std::endl;
}


void test_line_search_wall_constraint() {
    std::cout << "Testing line search with wall constraint..." << std::endl;
    
    // Create mesh with single triangle
    std::vector<Vec3> verts = {
        Vec3(0, 0, 0.1),  // Vertex above wall
        Vec3(1, 0, 0.1),
        Vec3(0.5, 1, 0.1)
    };
    std::vector<Triangle> tris = {Triangle(0, 1, 2)};
    
    Mesh mesh;
    Material mat;
    mesh.initialize(verts, tris, mat);
    
    State state;
    state.initialize(mesh);
    
    // Direction that would penetrate wall (downward)
    VecX direction = VecX::Zero(9);  // 3 vertices × 3 components
    direction[2] = -0.15;  // Move first vertex down through wall at z=0
    
    // Wall constraint
    Vec3 wall_normal(0, 0, 1);
    Real wall_offset = 0.0;
    
    // Empty contacts and pins
    std::vector<ContactPair> contacts;
    std::vector<Pin> pins;
    
    // Search with extension=1.0 for simpler test
    Real alpha = LineSearch::search(mesh, state, direction, contacts, pins, 
                                   wall_normal, wall_offset, 1.0);
    
    // Alpha should be reduced to prevent penetration
    assert(alpha < 1.0);
    assert(alpha > 0.0);
    
    std::cout << "  Alpha reduced to: " << alpha << " (< 1.0)" << std::endl;
    std::cout << "  ✓ Wall constraint line search passed" << std::endl;
}

void test_line_search_contact_constraint() {
    std::cout << "Testing line search with contact constraint..." << std::endl;
    
    // Create simple mesh with one moving vertex and one triangle
    std::vector<Vec3> verts = {
        // Moving vertex
        Vec3(0.5, 0.5, 0.5),
        // Triangle at z=0 (horizontal)
        Vec3(0, 0, 0),
        Vec3(1, 0, 0),
        Vec3(0.5, 1, 0)
    };
    std::vector<Triangle> tris = {
        Triangle(1, 2, 3)  // Only one triangle
    };
    
    Mesh mesh;
    Material mat;
    mesh.initialize(verts, tris, mat);
    
    State state;
    state.initialize(mesh);
    
    // Direction: move vertex 0 straight down through the triangle
    VecX direction = VecX::Zero(12);  // 4 vertices × 3 components
    direction[2] = -1.0;   // Vertex 0 moves down 1 unit (would penetrate)
    
    // Create contact constraint for vertex 0 vs triangle
    ContactPair contact;
    contact.type = ContactType::POINT_TRIANGLE;
    contact.idx0 = 0;  // Moving vertex
    contact.idx1 = 1;  // Triangle vertices
    contact.idx2 = 2;
    contact.idx3 = 3;
    contact.gap = 0.5;
    contact.normal = Vec3(0, 0, 1);
    
    std::vector<ContactPair> contacts = {contact};
    std::vector<Pin> pins;
    
    // No wall
    Vec3 wall_normal(0, 0, 0);
    Real wall_offset = 0.0;
    
    // Search with extension=1.0 for simplicity
    Real alpha = LineSearch::search(mesh, state, direction, contacts, pins,
                                   wall_normal, wall_offset, 1.0);
    
    std::cout << "  Alpha returned: " << alpha << std::endl;
    
    // Alpha should be reduced to prevent collision (full step would penetrate)
    if (alpha >= 1.0) {
        std::cout << "  WARNING: Alpha not reduced! Expected < 1.0" << std::endl;
        std::cout << "  This might indicate CCD is not detecting the collision." << std::endl;
    }
    assert(alpha < 1.0);
    
    std::cout << "  Alpha reduced to: " << alpha << " (< 1.0)" << std::endl;
    std::cout << "  ✓ Contact constraint line search passed" << std::endl;
}

void test_pcg_solver() {
    std::cout << "Testing PCG solver..." << std::endl;
    
    // Create a simple SPD system: A = I + small dense matrix
    const int n = 9;  // 3 vertices × 3 components
    SparseMatrix A(n, n);
    
    std::vector<Triplet> triplets;
    
    // Diagonal (identity)
    for (int i = 0; i < n; ++i) {
        triplets.push_back(Triplet(i, i, 2.0));
    }
    
    // Add some off-diagonal terms to make it interesting
    triplets.push_back(Triplet(0, 1, 0.5));
    triplets.push_back(Triplet(1, 0, 0.5));
    triplets.push_back(Triplet(3, 4, 0.3));
    triplets.push_back(Triplet(4, 3, 0.3));
    
    A.setFromTriplets(triplets.begin(), triplets.end());
    
    // Right-hand side
    VecX b = VecX::Ones(n);
    
    // Initial guess
    VecX x = VecX::Zero(n);
    
    // Solve
    bool converged = PCGSolver::solve(A, b, x, 1e-6, 100);
    
    assert(converged);
    
    // Check residual
    VecX r = b - A * x;
    Real residual = r.norm();
    
    std::cout << "  Solution norm: " << x.norm() << std::endl;
    std::cout << "  Residual norm: " << residual << std::endl;
    assert(residual < 1e-3);
    
    std::cout << "  ✓ PCG solver passed" << std::endl;
}
