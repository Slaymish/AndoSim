#include "../src/core/types.h"#include "../src/core/types.h"

#include "../src/core/barrier.h"#include "../src/core/barrier.h"

#include "../src/core/mesh.h"#include "../src/core/mesh.h"

#include "../src/core/state.h"#include "../src/core/state.h"

#include "../src/core/elasticity.h"#include "../src/core/stiffness.h"

#include "../src/core/stiffness.h"#include <iostream>

#include <iostream>#include <cassert>

#include <cassert>#include <cmath>

#include <cmath>

using namespace ando_barrier;

using namespace ando_barrier;

void test_stiffness_contact() {

// Test barrier energy computation    std::cout << "Testing contact stiffness computation..." << std::endl;

void test_barrier_energy() {    

    std::cout << "Testing barrier energy..." << std::endl;    Real mass = 0.1;  // kg

        Real dt = 0.01;   // seconds

    Real g_max = 0.01;  // 1cm    Real gap = 0.001; // m

    Real k = 1000.0;    // N/m    Vec3 normal(0.0, 0.0, 1.0);  // z direction

        

    // Test at g = g_max/2    // Simple diagonal Hessian

    Real g = g_max / 2.0;    Mat3 H = Mat3::Identity() * 1000.0;

    Real energy = Barrier::compute_energy(g, g_max, k);    

        Real k = Stiffness::compute_contact_stiffness(mass, dt, gap, normal, H);

    // Energy should be negative (attractive barrier)    

    assert(energy < 0.0);    // Expected: m/dt² + n·(H n) = 0.1/0.0001 + 1000 = 1000 + 1000 = 2000

    assert(std::isfinite(energy));    Real expected = mass / (dt * dt) + 1000.0;

        

    // Test at g = g_max (boundary)    std::cout << "  Computed stiffness: " << k << std::endl;

    Real energy_boundary = Barrier::compute_energy(g_max, g_max, k);    std::cout << "  Expected stiffness: " << expected << std::endl;

    assert(std::abs(energy_boundary) < 1e-6);  // Should be ~0    

        assert(std::abs(k - expected) < 1.0);

    // Test outside domain (g > g_max)    

    Real energy_outside = Barrier::compute_energy(g_max * 2.0, g_max, k);    std::cout << "  ✓ Contact stiffness test passed" << std::endl;

    assert(energy_outside == 0.0);}

    

    std::cout << "  ✓ Barrier energy test passed" << std::endl;void test_stiffness_pin() {

}    std::cout << "Testing pin stiffness computation..." << std::endl;

    

// Test barrier gradient    Real mass = 0.1;  // kg

void test_barrier_gradient() {    Real dt = 0.01;   // seconds

    std::cout << "Testing barrier gradient..." << std::endl;    Vec3 offset(0.1, 0.0, 0.0);  // Offset from pin target

        

    Real g_max = 0.01;    // Simple diagonal Hessian

    Real k = 1000.0;    Mat3 H = Mat3::Identity() * 500.0;

    Real g = g_max / 2.0;    

        Real k = Stiffness::compute_pin_stiffness(mass, dt, offset, H);

    Real grad = Barrier::compute_gradient(g, g_max, k);    

        // Expected: m/dt² + w·(H w) where w is normalized offset

    // Gradient should be negative (repulsive force)    // = 0.1/0.0001 + 500 = 1000 + 500 = 1500

    assert(grad < 0.0);    Real expected = mass / (dt * dt) + 500.0;

    assert(std::isfinite(grad));    

        std::cout << "  Computed stiffness: " << k << std::endl;

    // Test outside domain    std::cout << "  Expected stiffness: " << expected << std::endl;

    Real grad_outside = Barrier::compute_gradient(g_max * 2.0, g_max, k);    

    assert(grad_outside == 0.0);    assert(std::abs(k - expected) < 1.0);

        

    std::cout << "  ✓ Barrier gradient test passed" << std::endl;    std::cout << "  ✓ Pin stiffness test passed" << std::endl;

}}



// Test barrier Hessianvoid test_stiffness_takeover() {

void test_barrier_hessian() {    std::cout << "Testing stiffness takeover for small gaps..." << std::endl;

    std::cout << "Testing barrier Hessian..." << std::endl;    

        Real mass = 0.1;  // kg

    Real g_max = 0.01;    Real dt = 0.01;   // seconds

    Real k = 1000.0;    Real gap_large = 0.01;   // Normal gap

    Real g = g_max / 2.0;    Real gap_tiny = 1e-5;    // Tiny gap (below threshold)

        Vec3 normal(0.0, 0.0, 1.0);

    Real hess = Barrier::compute_hessian(g, g_max, k);    Mat3 H = Mat3::Identity() * 1000.0;

        

    // Hessian should be positive (convex repulsion)    Real k_large = Stiffness::compute_contact_stiffness(mass, dt, gap_large, normal, H);

    assert(hess > 0.0);    Real k_tiny = Stiffness::compute_contact_stiffness(mass, dt, gap_tiny, normal, H);

    assert(std::isfinite(hess));    

        std::cout << "  Stiffness at gap=0.01: " << k_large << std::endl;

    // Test outside domain    std::cout << "  Stiffness at gap=1e-5: " << k_tiny << std::endl;

    Real hess_outside = Barrier::compute_hessian(g_max * 2.0, g_max, k);    

    assert(hess_outside == 0.0);    // Tiny gap should have much larger stiffness due to takeover

        assert(k_tiny > k_large * 10.0);

    std::cout << "  ✓ Barrier Hessian test passed" << std::endl;    

}    std::cout << "  ✓ Stiffness takeover test passed" << std::endl;

}

// Test version function

void test_version() {void test_elasticity_at_rest() {

    std::cout << "Testing version function..." << std::endl;    std::cout << "Testing elasticity energy at rest..." << std::endl;ticity.h"

    #include "../src/core/stiffness.h"

    std::string ver = version();#include <iostream>

    assert(!ver.empty());#include <cassert>

    #include <cmath>

    std::cout << "  Library version: " << ver << std::endl;

    std::cout << "  ✓ Version test passed" << std::endl;using namespace ando_barrier;

}

void test_barrier_energy() {

// Test elasticity gradient with finite difference validation    std::cout << "Testing barrier energy..." << std::endl;

void test_elasticity_gradient_finite_diff() {    

    std::cout << "Testing elasticity gradient (finite difference validation)..." << std::endl;    Real g = 0.5;

        Real g_max = 1.0;

    // Create a simple mesh: single triangle    Real k = 100.0;

    std::vector<Vec3> vertices = {    

        Vec3(0.0, 0.0, 0.0),    Real energy = Barrier::compute_energy(g, g_max, k);

        Vec3(1.0, 0.0, 0.0),    std::cout << "  Energy at g=0.5, g_max=1.0, k=100: " << energy << std::endl;

        Vec3(0.0, 1.0, 0.0)    

    };    // Energy should be positive (repulsive barrier) and finite

        assert(energy > 0.0);

    std::vector<Vec3i> triangles = {    assert(std::isfinite(energy));

        Vec3i(0, 1, 2)    

    };    // Energy outside domain should be zero

        Real energy_outside = Barrier::compute_energy(1.5, g_max, k);

    Mesh mesh;    assert(energy_outside == 0.0);

    mesh.initialize(vertices, triangles);    

        std::cout << "  ✓ Barrier energy test passed" << std::endl;

    // Create state at rest (should have F = I, energy = 0)}

    State state;

    state.initialize(mesh, 1000.0);  // densityvoid test_barrier_gradient() {

        std::cout << "Testing barrier gradient..." << std::endl;

    // Stretch the triangle a bit    

    Vec3 deformation(0.1, 0.0, 0.0);    Real g = 0.5;

    state.x[1] += deformation;  // Move vertex 1    Real g_max = 1.0;

        Real k = 100.0;

    // Material properties    

    Real youngs = 1e6;  // Pa    Real grad = Barrier::compute_gradient(g, g_max, k);

    Real poisson = 0.3;    std::cout << "  Gradient at g=0.5: " << grad << std::endl;

    Real thickness = 0.001;  // m    

    Real lame_mu = youngs / (2.0 * (1.0 + poisson));    assert(std::isfinite(grad));

    Real lame_lambda = youngs * poisson / ((1.0 + poisson) * (1.0 - 2.0 * poisson));    

    Real k_arap = lame_mu * thickness;    std::cout << "  ✓ Barrier gradient test passed" << std::endl;

    }

    // Compute analytic gradient

    Vec3 grad_analytic = Elasticity::face_gradient(mesh, state, 0, k_arap);void test_barrier_hessian() {

        std::cout << "Testing barrier Hessian..." << std::endl;

    // Compute numeric gradient for vertex 1    

    Real epsilon = 1e-5;    Real g = 0.5;

    Real energy_plus = 0.0, energy_minus = 0.0;    Real g_max = 1.0;

        Real k = 100.0;

    // Perturb in x direction    

    state.x[1][0] += epsilon;    Real hess = Barrier::compute_hessian(g, g_max, k);

    Mat2 F_plus = Elasticity::compute_F(mesh, state, 0);    std::cout << "  Hessian at g=0.5: " << hess << std::endl;

    energy_plus = k_arap * (F_plus - Mat2::Identity()).squaredNorm();    

        assert(std::isfinite(hess));

    state.x[1][0] -= 2.0 * epsilon;    

    Mat2 F_minus = Elasticity::compute_F(mesh, state, 0);    std::cout << "  ✓ Barrier Hessian test passed" << std::endl;

    energy_minus = k_arap * (F_minus - Mat2::Identity()).squaredNorm();}

    

    Real grad_numeric = (energy_plus - energy_minus) / (2.0 * epsilon);void test_version() {

        std::cout << "Testing version info..." << std::endl;

    // Restore state    std::cout << "  Version: " << VERSION_MAJOR << "." 

    state.x[1][0] += epsilon;              << VERSION_MINOR << "." << VERSION_PATCH << std::endl;

        std::cout << "  ✓ Version test passed" << std::endl;

    std::cout << "  Analytic gradient[0]: " << grad_analytic[0] << std::endl;}

    std::cout << "  Numeric gradient[0]:  " << grad_numeric << std::endl;

    void test_elasticity_gradient_finite_diff() {

    // Check relative error    std::cout << "Testing elasticity gradient with finite differences..." << std::endl;

    Real rel_error = std::abs(grad_analytic[0] - grad_numeric) / std::abs(grad_numeric);    

    std::cout << "  Relative error: " << rel_error * 100.0 << "%" << std::endl;    // Create a triangle mesh at REST

        std::vector<Vec3> rest_verts = {

    assert(rel_error < 0.05);  // 5% tolerance for single precision        Vec3(0.0, 0.0, 0.0),

            Vec3(1.0, 0.0, 0.0),

    std::cout << "  ✓ Elasticity gradient test passed" << std::endl;        Vec3(0.0, 1.0, 0.0)

}    };

    

// Test elasticity energy at rest    std::vector<Triangle> tris = { Triangle{0, 1, 2} };

void test_elasticity_at_rest() {    

    std::cout << "Testing elasticity energy at rest..." << std::endl;    Material mat;

        mat.youngs_modulus = 1e6;

    // Create a simple mesh: single triangle    mat.poisson_ratio = 0.3;

    std::vector<Vec3> vertices = {    mat.density = 1000.0;

        Vec3(0.0, 0.0, 0.0),    mat.thickness = 0.001;

        Vec3(1.0, 0.0, 0.0),    

        Vec3(0.0, 1.0, 0.0)    Mesh mesh;

    };    mesh.initialize(rest_verts, tris, mat);

        

    std::vector<Vec3i> triangles = {    // NOW deform it slightly

        Vec3i(0, 1, 2)    mesh.vertices[1][0] = 1.1;  // Stretch in x direction

    };    

        State state;

    Mesh mesh;    state.initialize(mesh);

    mesh.initialize(vertices, triangles);    

        // Compute analytic gradient

    // Create state at rest    VecX grad_analytic(mesh.num_vertices() * 3);

    State state;    Elasticity::compute_gradient(mesh, state, grad_analytic);

    state.initialize(mesh, 1000.0);    

        std::cout << "  Analytic gradient:" << std::endl;

    // Compute deformation gradient - should be identity at rest    for (int i = 0; i < 9; ++i) {

    Mat2 F = Elasticity::compute_F(mesh, state, 0);        std::cout << "    grad[" << i << "] = " << grad_analytic[i] << std::endl;

        }

    std::cout << "  F at rest:" << std::endl;    

    std::cout << "    " << F(0,0) << " " << F(0,1) << std::endl;    // Compute numeric gradient via finite differences

    std::cout << "    " << F(1,0) << " " << F(1,1) << std::endl;    Real eps = 1e-6;

        VecX grad_numeric(mesh.num_vertices() * 3);

    // F should be identity matrix    

    Mat2 I = Mat2::Identity();    for (size_t i = 0; i < mesh.num_vertices() * 3; ++i) {

    Real F_error = (F - I).norm();        // Perturb position

    std::cout << "  ||F - I||: " << F_error << std::endl;        mesh.vertices[i / 3][i % 3] += eps;

            Real e_plus = Elasticity::compute_energy(mesh, state);

    assert(F_error < 1e-5);        

            mesh.vertices[i / 3][i % 3] -= 2.0 * eps;

    // Energy should be zero at rest        Real e_minus = Elasticity::compute_energy(mesh, state);

    Real k_arap = 1000.0;        

    Real energy = k_arap * (F - I).squaredNorm();        // Restore

    std::cout << "  Energy at rest: " << energy << std::endl;        mesh.vertices[i / 3][i % 3] += eps;

            

    assert(energy < 1e-8);        grad_numeric[i] = (e_plus - e_minus) / (2.0 * eps);

        }

    std::cout << "  ✓ Elasticity at rest test passed" << std::endl;    

}    std::cout << "  Numeric gradient:" << std::endl;

    for (int i = 0; i < 9; ++i) {

// Test barrier gradient with numeric differentiation        std::cout << "    grad[" << i << "] = " << grad_numeric[i] << std::endl;

void test_barrier_numeric_gradient() {    }

    std::cout << "Testing barrier gradient (numeric validation)..." << std::endl;    

        // Compare

    Real g_max = 0.01;    Real max_error = 0.0;

    Real k = 1000.0;    for (size_t i = 0; i < grad_analytic.size(); ++i) {

    Real g = g_max / 2.0;        Real error = std::abs(grad_analytic[i] - grad_numeric[i]);

    Real epsilon = 1e-6;        Real relative_error = error / (std::abs(grad_numeric[i]) + 1e-10);

            if (relative_error > max_error && std::abs(grad_numeric[i]) > 1e-8) {

    // Analytic gradient            max_error = relative_error;

    Real grad_analytic = Barrier::compute_gradient(g, g_max, k);            std::cout << "  Max error at component " << i << ": abs=" << error 

                          << " rel=" << relative_error << std::endl;

    // Numeric gradient        }

    Real E_plus = Barrier::compute_energy(g + epsilon, g_max, k);    }

    Real E_minus = Barrier::compute_energy(g - epsilon, g_max, k);    

    Real grad_numeric = (E_plus - E_minus) / (2.0 * epsilon);    std::cout << "  Max relative error: " << max_error << std::endl;

        

    std::cout << "  Analytic gradient: " << grad_analytic << std::endl;    // Check tolerance (float precision allows ~1e-4 relative error)

    std::cout << "  Numeric gradient:  " << grad_numeric << std::endl;    assert(max_error < 0.05);  // 5% tolerance for now

        

    Real rel_error = std::abs(grad_analytic - grad_numeric) / std::abs(grad_numeric);    std::cout << "  ✓ Elasticity gradient test passed" << std::endl;

    std::cout << "  Relative error: " << rel_error * 100.0 << "%" << std::endl;}

    

    assert(rel_error < 0.002);  // 0.2% tolerancevoid test_elasticity_at_rest() {

        std::cout << "Testing elasticity energy at rest..." << std::endl;

    std::cout << "  ✓ Barrier numeric gradient test passed" << std::endl;    

}    // Create a triangle at rest

    std::vector<Vec3> verts = {

// Test barrier Hessian with numeric differentiation        Vec3(0.0, 0.0, 0.0),

void test_barrier_numeric_hessian() {        Vec3(1.0, 0.0, 0.0),

    std::cout << "Testing barrier Hessian (numeric validation)..." << std::endl;        Vec3(0.0, 1.0, 0.0)

        };

    Real g_max = 0.01;    

    Real k = 1000.0;    std::vector<Triangle> tris = { Triangle{0, 1, 2} };

    Real g = g_max / 2.0;    

    Real epsilon = 1e-6;    Material mat;

        mat.youngs_modulus = 1e6;

    // Analytic Hessian    mat.poisson_ratio = 0.3;

    Real hess_analytic = Barrier::compute_hessian(g, g_max, k);    mat.density = 1000.0;

        mat.thickness = 0.001;

    // Numeric Hessian (second derivative)    

    Real grad_plus = Barrier::compute_gradient(g + epsilon, g_max, k);    Mesh mesh;

    Real grad_minus = Barrier::compute_gradient(g - epsilon, g_max, k);    mesh.initialize(verts, tris, mat);

    Real hess_numeric = (grad_plus - grad_minus) / (2.0 * epsilon);    

        State state;

    std::cout << "  Analytic Hessian: " << hess_analytic << std::endl;    state.initialize(mesh);

    std::cout << "  Numeric Hessian:  " << hess_numeric << std::endl;    

        // Energy should be zero at rest (F = I)

    Real rel_error = std::abs(hess_analytic - hess_numeric) / std::abs(hess_numeric);    Real energy = Elasticity::compute_energy(mesh, state);

    std::cout << "  Relative error: " << rel_error * 100.0 << "%" << std::endl;    std::cout << "  Energy at rest: " << energy << std::endl;

        

    assert(rel_error < 0.002);  // 0.2% tolerance    assert(std::abs(energy) < 1e-6);

        

    std::cout << "  ✓ Barrier numeric Hessian test passed" << std::endl;    // Gradient should be zero at rest

}    VecX gradient(mesh.num_vertices() * 3);

    Elasticity::compute_gradient(mesh, state, gradient);

// Test C² continuity at boundary    

void test_barrier_c2_smoothness() {    Real grad_norm = gradient.norm();

    std::cout << "Testing barrier C² smoothness at boundary..." << std::endl;    std::cout << "  Gradient norm at rest: " << grad_norm << std::endl;

        

    Real g_max = 0.01;    assert(grad_norm < 1e-6);

    Real k = 1000.0;    

    Real delta = 1e-8;    std::cout << "  ✓ Elasticity at rest test passed" << std::endl;

    }

    // Just inside boundary

    Real g_inside = g_max - delta;void test_barrier_numeric_gradient() {

    Real E_inside = Barrier::compute_energy(g_inside, g_max, k);    std::cout << "Testing barrier gradient numerically..." << std::endl;

    Real grad_inside = Barrier::compute_gradient(g_inside, g_max, k);    

    Real hess_inside = Barrier::compute_hessian(g_inside, g_max, k);    Real g = 0.5;

        Real g_max = 1.0;

    // At boundary    Real k = 100.0;

    Real E_boundary = Barrier::compute_energy(g_max, g_max, k);    Real eps = 1e-5;

    Real grad_boundary = Barrier::compute_gradient(g_max, g_max, k);    

    Real hess_boundary = Barrier::compute_hessian(g_max, g_max, k);    Real e_0 = Barrier::compute_energy(g, g_max, k);

        Real e_plus = Barrier::compute_energy(g + eps, g_max, k);

    // Just outside boundary    Real e_minus = Barrier::compute_energy(g - eps, g_max, k);

    Real g_outside = g_max + delta;    

    Real E_outside = Barrier::compute_energy(g_outside, g_max, k);    std::cout << "  E(g-eps): " << e_minus << std::endl;

    Real grad_outside = Barrier::compute_gradient(g_outside, g_max, k);    std::cout << "  E(g):     " << e_0 << std::endl;

    Real hess_outside = Barrier::compute_hessian(g_outside, g_max, k);    std::cout << "  E(g+eps): " << e_plus << std::endl;

        

    std::cout << "  Energy: inside=" << E_inside << ", boundary=" << E_boundary << ", outside=" << E_outside << std::endl;    Real grad_analytic = Barrier::compute_gradient(g, g_max, k);

    std::cout << "  Gradient: inside=" << grad_inside << ", boundary=" << grad_boundary << ", outside=" << grad_outside << std::endl;    Real grad_numeric = (e_plus - e_minus) / (2.0 * eps);

    std::cout << "  Hessian: inside=" << hess_inside << ", boundary=" << hess_boundary << ", outside=" << hess_outside << std::endl;    

        Real error = std::abs(grad_analytic - grad_numeric);

    // All should be very small near boundary    Real relative_error = error / (std::abs(grad_numeric) + 1e-10);

    assert(std::abs(E_boundary) < 1e-6);    

    assert(std::abs(grad_boundary) < 1e-3);    std::cout << "  Analytic gradient: " << grad_analytic << std::endl;

    assert(std::abs(hess_boundary) < 100.0);    std::cout << "  Numeric gradient: " << grad_numeric << std::endl;

        std::cout << "  Absolute error: " << error << std::endl;

    std::cout << "  ✓ Barrier C² smoothness test passed" << std::endl;    std::cout << "  Relative error: " << relative_error << std::endl;

}    

    // More tolerant check for single precision

// Test contact stiffness computation    assert(relative_error < 0.02);  // 2% tolerance

void test_stiffness_contact() {    

    std::cout << "Testing contact stiffness computation..." << std::endl;    std::cout << "  ✓ Barrier numeric gradient test passed" << std::endl;

    }

    Real mass = 0.1;  // kg

    Real dt = 0.01;   // secondsvoid test_barrier_numeric_hessian() {

    Real gap = 0.001; // m    std::cout << "Testing barrier Hessian numerically..." << std::endl;

    Vec3 normal(0.0, 0.0, 1.0);  // z direction    

        Real g = 0.5;

    // Simple diagonal Hessian    Real g_max = 1.0;

    Mat3 H = Mat3::Identity() * 1000.0;    Real k = 100.0;

        Real eps = 1e-5;

    Real k = Stiffness::compute_contact_stiffness(mass, dt, gap, normal, H);    

        Real hess_analytic = Barrier::compute_hessian(g, g_max, k);

    // Expected: m/dt² + n·(H n) = 0.1/0.0001 + 1000 = 1000 + 1000 = 2000    

    Real expected = mass / (dt * dt) + 1000.0;    Real grad_plus = Barrier::compute_gradient(g + eps, g_max, k);

        Real grad_minus = Barrier::compute_gradient(g - eps, g_max, k);

    std::cout << "  Computed stiffness: " << k << std::endl;    Real hess_numeric = (grad_plus - grad_minus) / (2.0 * eps);

    std::cout << "  Expected stiffness: " << expected << std::endl;    

        Real error = std::abs(hess_analytic - hess_numeric);

    assert(std::abs(k - expected) < 1.0);    Real relative_error = error / (std::abs(hess_numeric) + 1e-10);

        

    std::cout << "  ✓ Contact stiffness test passed" << std::endl;    std::cout << "  Analytic Hessian: " << hess_analytic << std::endl;

}    std::cout << "  Numeric Hessian: " << hess_numeric << std::endl;

    std::cout << "  Absolute error: " << error << std::endl;

// Test pin stiffness computation    std::cout << "  Relative error: " << relative_error << std::endl;

void test_stiffness_pin() {    

    std::cout << "Testing pin stiffness computation..." << std::endl;    // More tolerant for second derivatives with single precision

        assert(relative_error < 0.05);  // 5% tolerance

    Real mass = 0.1;  // kg    

    Real dt = 0.01;   // seconds    std::cout << "  ✓ Barrier numeric Hessian test passed" << std::endl;

    Vec3 offset(0.1, 0.0, 0.0);  // Offset from pin target}

    

    // Simple diagonal Hessianvoid test_barrier_c2_smoothness() {

    Mat3 H = Mat3::Identity() * 500.0;    std::cout << "Testing barrier C² smoothness at boundary..." << std::endl;

        

    Real k = Stiffness::compute_pin_stiffness(mass, dt, offset, H);    Real g_max = 1.0;

        Real k = 100.0;

    // Expected: m/dt² + w·(H w) where w is normalized offset    Real eps = 1e-6;

    // = 0.1/0.0001 + 500 = 1000 + 500 = 1500    

    Real expected = mass / (dt * dt) + 500.0;    // Test near g = g_max boundary

        Real g_inside = g_max - eps;

    std::cout << "  Computed stiffness: " << k << std::endl;    Real g_outside = g_max + eps;

    std::cout << "  Expected stiffness: " << expected << std::endl;    

        // Energy should go to zero smoothly

    assert(std::abs(k - expected) < 1.0);    Real e_inside = Barrier::compute_energy(g_inside, g_max, k);

        Real e_outside = Barrier::compute_energy(g_outside, g_max, k);

    std::cout << "  ✓ Pin stiffness test passed" << std::endl;    

}    std::cout << "  Energy just inside: " << e_inside << std::endl;

    std::cout << "  Energy just outside: " << e_outside << std::endl;

// Test stiffness takeover for small gaps    

void test_stiffness_takeover() {    assert(e_outside == 0.0);

    std::cout << "Testing stiffness takeover for small gaps..." << std::endl;    assert(e_inside >= 0.0 && e_inside < 1e-4);  // Should be very small

        

    Real mass = 0.1;  // kg    // Gradient should also go to zero

    Real dt = 0.01;   // seconds    Real grad_inside = Barrier::compute_gradient(g_inside, g_max, k);

    Real gap_large = 0.01;   // Normal gap    Real grad_outside = Barrier::compute_gradient(g_outside, g_max, k);

    Real gap_tiny = 1e-5;    // Tiny gap (below threshold)    

    Vec3 normal(0.0, 0.0, 1.0);    std::cout << "  Gradient just inside: " << grad_inside << std::endl;

    Mat3 H = Mat3::Identity() * 1000.0;    std::cout << "  Gradient just outside: " << grad_outside << std::endl;

        

    Real k_large = Stiffness::compute_contact_stiffness(mass, dt, gap_large, normal, H);    assert(grad_outside == 0.0);

    Real k_tiny = Stiffness::compute_contact_stiffness(mass, dt, gap_tiny, normal, H);    assert(std::abs(grad_inside) < 1.0);  // Should be small

        

    std::cout << "  Stiffness at gap=0.01: " << k_large << std::endl;    std::cout << "  ✓ Barrier C² smoothness test passed" << std::endl;

    std::cout << "  Stiffness at gap=1e-5: " << k_tiny << std::endl;}

    

    // Tiny gap should have much larger stiffness due to takeoverint main() {

    assert(k_tiny > k_large * 10.0);    std::cout << "========================================" << std::endl;

        std::cout << "Ando Barrier Core - Basic Tests" << std::endl;

    std::cout << "  ✓ Stiffness takeover test passed" << std::endl;    std::cout << "========================================" << std::endl;

}    

    try {

int main() {        test_version();

    std::cout << "\n========================================" << std::endl;        

    std::cout << "Ando Barrier Core - Unit Tests" << std::endl;        std::cout << "\n--- Barrier Tests ---" << std::endl;

    std::cout << "========================================\n" << std::endl;        test_barrier_energy();

            test_barrier_gradient();

    test_version();        test_barrier_hessian();

    test_barrier_energy();        test_barrier_numeric_gradient();

    test_barrier_gradient();        test_barrier_numeric_hessian();

    test_barrier_hessian();        test_barrier_c2_smoothness();

    test_barrier_numeric_gradient();        

    test_barrier_numeric_hessian();        std::cout << "\n--- Elasticity Tests ---" << std::endl;

    test_barrier_c2_smoothness();        test_elasticity_at_rest();

    test_elasticity_at_rest();        test_elasticity_gradient_finite_diff();

    test_elasticity_gradient_finite_diff();        

    test_stiffness_contact();        std::cout << "\n--- Stiffness Tests ---" << std::endl;

    test_stiffness_pin();        test_stiffness_contact();

    test_stiffness_takeover();        test_stiffness_pin();

            test_stiffness_takeover();

    std::cout << "\n========================================" << std::endl;        

    std::cout << "All tests passed! ✓" << std::endl;        std::cout << "\n========================================" << std::endl;

    std::cout << "========================================\n" << std::endl;        std::cout << "All tests passed!" << std::endl;

            std::cout << "========================================" << std::endl;

    return 0;        return 0;

}    } catch (const std::exception& e) {

        std::cerr << "Test failed with exception: " << e.what() << std::endl;
        return 1;
    }
}
