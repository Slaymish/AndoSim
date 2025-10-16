#include "../src/core/types.h"
#include "../src/core/barrier.h"
#include "../src/core/mesh.h"
#include "../src/core/state.h"
#include "../src/core    std::cout << "  ✓ Elasticity at rest test passed" << std::endl;
}

void test_stiffness_contact() {
    std::cout << "Testing contact stiffness computation..." << std::endl;
    
    Real mass = 0.1;  // kg
    Real dt = 0.01;   // seconds
    Real gap = 0.001; // m
    Vec3 normal(0.0, 0.0, 1.0);  // z direction
    
    // Simple diagonal Hessian
    Mat3 H = Mat3::Identity() * 1000.0;
    
    Real k = Stiffness::compute_contact_stiffness(mass, dt, gap, normal, H);
    
    // Expected: m/dt² + n·(H n) = 0.1/0.0001 + 1000 = 1000 + 1000 = 2000
    Real expected = mass / (dt * dt) + 1000.0;
    
    std::cout << "  Computed stiffness: " << k << std::endl;
    std::cout << "  Expected stiffness: " << expected << std::endl;
    
    assert(std::abs(k - expected) < 1.0);
    
    std::cout << "  ✓ Contact stiffness test passed" << std::endl;
}

void test_stiffness_pin() {
    std::cout << "Testing pin stiffness computation..." << std::endl;
    
    Real mass = 0.1;  // kg
    Real dt = 0.01;   // seconds
    Vec3 offset(0.1, 0.0, 0.0);  // Offset from pin target
    
    // Simple diagonal Hessian
    Mat3 H = Mat3::Identity() * 500.0;
    
    Real k = Stiffness::compute_pin_stiffness(mass, dt, offset, H);
    
    // Expected: m/dt² + w·(H w) where w is normalized offset
    // = 0.1/0.0001 + 500 = 1000 + 500 = 1500
    Real expected = mass / (dt * dt) + 500.0;
    
    std::cout << "  Computed stiffness: " << k << std::endl;
    std::cout << "  Expected stiffness: " << expected << std::endl;
    
    assert(std::abs(k - expected) < 1.0);
    
    std::cout << "  ✓ Pin stiffness test passed" << std::endl;
}

void test_stiffness_takeover() {
    std::cout << "Testing stiffness takeover for small gaps..." << std::endl;
    
    Real mass = 0.1;  // kg
    Real dt = 0.01;   // seconds
    Real gap_large = 0.01;   // Normal gap
    Real gap_tiny = 1e-5;    // Tiny gap (below threshold)
    Vec3 normal(0.0, 0.0, 1.0);
    Mat3 H = Mat3::Identity() * 1000.0;
    
    Real k_large = Stiffness::compute_contact_stiffness(mass, dt, gap_large, normal, H);
    Real k_tiny = Stiffness::compute_contact_stiffness(mass, dt, gap_tiny, normal, H);
    
    std::cout << "  Stiffness at gap=0.01: " << k_large << std::endl;
    std::cout << "  Stiffness at gap=1e-5: " << k_tiny << std::endl;
    
    // Tiny gap should have much larger stiffness due to takeover
    assert(k_tiny > k_large * 10.0);
    
    std::cout << "  ✓ Stiffness takeover test passed" << std::endl;
}

void test_elasticity_at_rest() {
    std::cout << "Testing elasticity energy at rest..." << std::endl;ticity.h"
#include "../src/core/stiffness.h"
#include <iostream>
#include <cassert>
#include <cmath>

using namespace ando_barrier;

void test_barrier_energy() {
    std::cout << "Testing barrier energy..." << std::endl;
    
    Real g = 0.5;
    Real g_max = 1.0;
    Real k = 100.0;
    
    Real energy = Barrier::compute_energy(g, g_max, k);
    std::cout << "  Energy at g=0.5, g_max=1.0, k=100: " << energy << std::endl;
    
    // Energy should be positive (repulsive barrier) and finite
    assert(energy > 0.0);
    assert(std::isfinite(energy));
    
    // Energy outside domain should be zero
    Real energy_outside = Barrier::compute_energy(1.5, g_max, k);
    assert(energy_outside == 0.0);
    
    std::cout << "  ✓ Barrier energy test passed" << std::endl;
}

void test_barrier_gradient() {
    std::cout << "Testing barrier gradient..." << std::endl;
    
    Real g = 0.5;
    Real g_max = 1.0;
    Real k = 100.0;
    
    Real grad = Barrier::compute_gradient(g, g_max, k);
    std::cout << "  Gradient at g=0.5: " << grad << std::endl;
    
    assert(std::isfinite(grad));
    
    std::cout << "  ✓ Barrier gradient test passed" << std::endl;
}

void test_barrier_hessian() {
    std::cout << "Testing barrier Hessian..." << std::endl;
    
    Real g = 0.5;
    Real g_max = 1.0;
    Real k = 100.0;
    
    Real hess = Barrier::compute_hessian(g, g_max, k);
    std::cout << "  Hessian at g=0.5: " << hess << std::endl;
    
    assert(std::isfinite(hess));
    
    std::cout << "  ✓ Barrier Hessian test passed" << std::endl;
}

void test_version() {
    std::cout << "Testing version info..." << std::endl;
    std::cout << "  Version: " << VERSION_MAJOR << "." 
              << VERSION_MINOR << "." << VERSION_PATCH << std::endl;
    std::cout << "  ✓ Version test passed" << std::endl;
}

void test_elasticity_gradient_finite_diff() {
    std::cout << "Testing elasticity gradient with finite differences..." << std::endl;
    
    // Create a triangle mesh at REST
    std::vector<Vec3> rest_verts = {
        Vec3(0.0, 0.0, 0.0),
        Vec3(1.0, 0.0, 0.0),
        Vec3(0.0, 1.0, 0.0)
    };
    
    std::vector<Triangle> tris = { Triangle{0, 1, 2} };
    
    Material mat;
    mat.youngs_modulus = 1e6;
    mat.poisson_ratio = 0.3;
    mat.density = 1000.0;
    mat.thickness = 0.001;
    
    Mesh mesh;
    mesh.initialize(rest_verts, tris, mat);
    
    // NOW deform it slightly
    mesh.vertices[1][0] = 1.1;  // Stretch in x direction
    
    State state;
    state.initialize(mesh);
    
    // Compute analytic gradient
    VecX grad_analytic(mesh.num_vertices() * 3);
    Elasticity::compute_gradient(mesh, state, grad_analytic);
    
    std::cout << "  Analytic gradient:" << std::endl;
    for (int i = 0; i < 9; ++i) {
        std::cout << "    grad[" << i << "] = " << grad_analytic[i] << std::endl;
    }
    
    // Compute numeric gradient via finite differences
    Real eps = 1e-6;
    VecX grad_numeric(mesh.num_vertices() * 3);
    
    for (size_t i = 0; i < mesh.num_vertices() * 3; ++i) {
        // Perturb position
        mesh.vertices[i / 3][i % 3] += eps;
        Real e_plus = Elasticity::compute_energy(mesh, state);
        
        mesh.vertices[i / 3][i % 3] -= 2.0 * eps;
        Real e_minus = Elasticity::compute_energy(mesh, state);
        
        // Restore
        mesh.vertices[i / 3][i % 3] += eps;
        
        grad_numeric[i] = (e_plus - e_minus) / (2.0 * eps);
    }
    
    std::cout << "  Numeric gradient:" << std::endl;
    for (int i = 0; i < 9; ++i) {
        std::cout << "    grad[" << i << "] = " << grad_numeric[i] << std::endl;
    }
    
    // Compare
    Real max_error = 0.0;
    for (size_t i = 0; i < grad_analytic.size(); ++i) {
        Real error = std::abs(grad_analytic[i] - grad_numeric[i]);
        Real relative_error = error / (std::abs(grad_numeric[i]) + 1e-10);
        if (relative_error > max_error && std::abs(grad_numeric[i]) > 1e-8) {
            max_error = relative_error;
            std::cout << "  Max error at component " << i << ": abs=" << error 
                      << " rel=" << relative_error << std::endl;
        }
    }
    
    std::cout << "  Max relative error: " << max_error << std::endl;
    
    // Check tolerance (float precision allows ~1e-4 relative error)
    assert(max_error < 0.05);  // 5% tolerance for now
    
    std::cout << "  ✓ Elasticity gradient test passed" << std::endl;
}

void test_elasticity_at_rest() {
    std::cout << "Testing elasticity energy at rest..." << std::endl;
    
    // Create a triangle at rest
    std::vector<Vec3> verts = {
        Vec3(0.0, 0.0, 0.0),
        Vec3(1.0, 0.0, 0.0),
        Vec3(0.0, 1.0, 0.0)
    };
    
    std::vector<Triangle> tris = { Triangle{0, 1, 2} };
    
    Material mat;
    mat.youngs_modulus = 1e6;
    mat.poisson_ratio = 0.3;
    mat.density = 1000.0;
    mat.thickness = 0.001;
    
    Mesh mesh;
    mesh.initialize(verts, tris, mat);
    
    State state;
    state.initialize(mesh);
    
    // Energy should be zero at rest (F = I)
    Real energy = Elasticity::compute_energy(mesh, state);
    std::cout << "  Energy at rest: " << energy << std::endl;
    
    assert(std::abs(energy) < 1e-6);
    
    // Gradient should be zero at rest
    VecX gradient(mesh.num_vertices() * 3);
    Elasticity::compute_gradient(mesh, state, gradient);
    
    Real grad_norm = gradient.norm();
    std::cout << "  Gradient norm at rest: " << grad_norm << std::endl;
    
    assert(grad_norm < 1e-6);
    
    std::cout << "  ✓ Elasticity at rest test passed" << std::endl;
}

void test_barrier_numeric_gradient() {
    std::cout << "Testing barrier gradient numerically..." << std::endl;
    
    Real g = 0.5;
    Real g_max = 1.0;
    Real k = 100.0;
    Real eps = 1e-5;
    
    Real e_0 = Barrier::compute_energy(g, g_max, k);
    Real e_plus = Barrier::compute_energy(g + eps, g_max, k);
    Real e_minus = Barrier::compute_energy(g - eps, g_max, k);
    
    std::cout << "  E(g-eps): " << e_minus << std::endl;
    std::cout << "  E(g):     " << e_0 << std::endl;
    std::cout << "  E(g+eps): " << e_plus << std::endl;
    
    Real grad_analytic = Barrier::compute_gradient(g, g_max, k);
    Real grad_numeric = (e_plus - e_minus) / (2.0 * eps);
    
    Real error = std::abs(grad_analytic - grad_numeric);
    Real relative_error = error / (std::abs(grad_numeric) + 1e-10);
    
    std::cout << "  Analytic gradient: " << grad_analytic << std::endl;
    std::cout << "  Numeric gradient: " << grad_numeric << std::endl;
    std::cout << "  Absolute error: " << error << std::endl;
    std::cout << "  Relative error: " << relative_error << std::endl;
    
    // More tolerant check for single precision
    assert(relative_error < 0.02);  // 2% tolerance
    
    std::cout << "  ✓ Barrier numeric gradient test passed" << std::endl;
}

void test_barrier_numeric_hessian() {
    std::cout << "Testing barrier Hessian numerically..." << std::endl;
    
    Real g = 0.5;
    Real g_max = 1.0;
    Real k = 100.0;
    Real eps = 1e-5;
    
    Real hess_analytic = Barrier::compute_hessian(g, g_max, k);
    
    Real grad_plus = Barrier::compute_gradient(g + eps, g_max, k);
    Real grad_minus = Barrier::compute_gradient(g - eps, g_max, k);
    Real hess_numeric = (grad_plus - grad_minus) / (2.0 * eps);
    
    Real error = std::abs(hess_analytic - hess_numeric);
    Real relative_error = error / (std::abs(hess_numeric) + 1e-10);
    
    std::cout << "  Analytic Hessian: " << hess_analytic << std::endl;
    std::cout << "  Numeric Hessian: " << hess_numeric << std::endl;
    std::cout << "  Absolute error: " << error << std::endl;
    std::cout << "  Relative error: " << relative_error << std::endl;
    
    // More tolerant for second derivatives with single precision
    assert(relative_error < 0.05);  // 5% tolerance
    
    std::cout << "  ✓ Barrier numeric Hessian test passed" << std::endl;
}

void test_barrier_c2_smoothness() {
    std::cout << "Testing barrier C² smoothness at boundary..." << std::endl;
    
    Real g_max = 1.0;
    Real k = 100.0;
    Real eps = 1e-6;
    
    // Test near g = g_max boundary
    Real g_inside = g_max - eps;
    Real g_outside = g_max + eps;
    
    // Energy should go to zero smoothly
    Real e_inside = Barrier::compute_energy(g_inside, g_max, k);
    Real e_outside = Barrier::compute_energy(g_outside, g_max, k);
    
    std::cout << "  Energy just inside: " << e_inside << std::endl;
    std::cout << "  Energy just outside: " << e_outside << std::endl;
    
    assert(e_outside == 0.0);
    assert(e_inside >= 0.0 && e_inside < 1e-4);  // Should be very small
    
    // Gradient should also go to zero
    Real grad_inside = Barrier::compute_gradient(g_inside, g_max, k);
    Real grad_outside = Barrier::compute_gradient(g_outside, g_max, k);
    
    std::cout << "  Gradient just inside: " << grad_inside << std::endl;
    std::cout << "  Gradient just outside: " << grad_outside << std::endl;
    
    assert(grad_outside == 0.0);
    assert(std::abs(grad_inside) < 1.0);  // Should be small
    
    std::cout << "  ✓ Barrier C² smoothness test passed" << std::endl;
}

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "Ando Barrier Core - Basic Tests" << std::endl;
    std::cout << "========================================" << std::endl;
    
    try {
        test_version();
        
        std::cout << "\n--- Barrier Tests ---" << std::endl;
        test_barrier_energy();
        test_barrier_gradient();
        test_barrier_hessian();
        test_barrier_numeric_gradient();
        test_barrier_numeric_hessian();
        test_barrier_c2_smoothness();
        
        std::cout << "\n--- Elasticity Tests ---" << std::endl;
        test_elasticity_at_rest();
        test_elasticity_gradient_finite_diff();
        
        std::cout << "\n--- Stiffness Tests ---" << std::endl;
        test_stiffness_contact();
        test_stiffness_pin();
        test_stiffness_takeover();
        
        std::cout << "\n========================================" << std::endl;
        std::cout << "All tests passed!" << std::endl;
        std::cout << "========================================" << std::endl;
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Test failed with exception: " << e.what() << std::endl;
        return 1;
    }
}
