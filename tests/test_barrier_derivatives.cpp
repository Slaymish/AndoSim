/**
 * Comprehensive numerical validation of barrier function derivatives
 * against finite differences to verify mathematical correctness
 */

#include "../src/core/barrier.h"
#include <iostream>
#include <cmath>
#include <cassert>
#include <iomanip>

using namespace ando_barrier;

const Real EPSILON = 1e-5;  // Finite difference step
const Real TOLERANCE = 1e-3; // Relative error tolerance (0.1%)

/**
 * Test barrier scalar function V_weak(g, ḡ, k) against cubic form:
 * V_weak(g, ḡ, k) = (k/(2ḡ)) (ḡ - g)^3 for g ≤ ḡ, else 0
 */
void test_barrier_energy_formula() {
    std::cout << "Testing V_weak energy formula..." << std::endl;
    
    Real g = 0.005;      // 5mm gap
    Real g_max = 0.01;   // 10mm max gap
    Real k = 1000.0;     // Stiffness
    
    // Compute via implementation
    Real V = Barrier::compute_energy(g, g_max, k);
    
    // Compute manually from cubic form
    Real diff = g_max - g;
    Real V_expected = 0.5 * k * diff * diff * diff / g_max;
    
    Real error = std::abs(V - V_expected);
    Real rel_error = error / std::abs(V_expected);
    
    std::cout << "  V_computed  = " << V << std::endl;
    std::cout << "  V_expected  = " << V_expected << std::endl;
    std::cout << "  Rel error   = " << rel_error * 100 << "%" << std::endl;
    
    assert(rel_error < TOLERANCE);
    std::cout << "  ✓ Energy formula matches paper" << std::endl;
}

/**
 * Test gradient dV/dg against numerical differentiation
 */
void test_barrier_gradient_numeric() {
    std::cout << "\nTesting dV/dg gradient (numeric)..." << std::endl;
    
    Real g = 0.005;
    Real g_max = 0.01;
    Real k = 1000.0;
    
    // Analytic gradient from implementation
    Real grad_analytic = Barrier::compute_gradient(g, g_max, k);
    
    // Numeric gradient via central differences
    Real V_plus = Barrier::compute_energy(g + EPSILON, g_max, k);
    Real V_minus = Barrier::compute_energy(g - EPSILON, g_max, k);
    Real grad_numeric = (V_plus - V_minus) / (2.0 * EPSILON);
    
    Real error = std::abs(grad_analytic - grad_numeric);
    Real rel_error = error / std::abs(grad_numeric);
    
    std::cout << "  dV/dg analytic = " << grad_analytic << std::endl;
    std::cout << "  dV/dg numeric  = " << grad_numeric << std::endl;
    std::cout << "  Rel error      = " << rel_error * 100 << "%" << std::endl;
    
    assert(rel_error < TOLERANCE);
    std::cout << "  ✓ Gradient matches numeric differentiation" << std::endl;
}

/**
 * Test Hessian d²V/dg² against numerical differentiation
 */
void test_barrier_hessian_numeric() {
    std::cout << "\nTesting d²V/dg² Hessian (numeric)..." << std::endl;
    
    Real g = 0.005;
    Real g_max = 0.01;
    Real k = 1000.0;
    
    // Analytic Hessian from implementation
    Real hess_analytic = Barrier::compute_hessian(g, g_max, k);
    
    // Numeric Hessian via finite differences of gradient
    Real grad_plus = Barrier::compute_gradient(g + EPSILON, g_max, k);
    Real grad_minus = Barrier::compute_gradient(g - EPSILON, g_max, k);
    Real hess_numeric = (grad_plus - grad_minus) / (2.0 * EPSILON);
    
    Real error = std::abs(hess_analytic - hess_numeric);
    Real rel_error = error / std::abs(hess_numeric);
    
    std::cout << "  d²V/dg² analytic = " << hess_analytic << std::endl;
    std::cout << "  d²V/dg² numeric  = " << hess_numeric << std::endl;
    std::cout << "  Rel error        = " << rel_error * 100 << "%" << std::endl;
    
    assert(rel_error < TOLERANCE);
    std::cout << "  ✓ Hessian matches numeric differentiation" << std::endl;
}

/**
 * Test domain boundaries: g=0, g=ḡ, g>ḡ
 */
void test_barrier_domain() {
    std::cout << "\nTesting barrier domain boundaries..." << std::endl;
    
    Real g_max = 0.01;
    Real k = 1000.0;
    
    // Test g > g_max (outside barrier domain)
    Real V_outside = Barrier::compute_energy(0.015, g_max, k);
    assert(V_outside == 0.0);
    std::cout << "  ✓ V=0 for g > ḡ" << std::endl;
    
    // Test g = g_max (boundary)
    Real V_boundary = Barrier::compute_energy(g_max, g_max, k);
    assert(V_boundary == 0.0);
    std::cout << "  ✓ V=0 at g = ḡ" << std::endl;
    
    // Test g ≤ 0 (penetration produces positive energy)
    Real V_negative = Barrier::compute_energy(-0.001, g_max, k);
    assert(V_negative > 0.0);
    std::cout << "  ✓ V>0 for g ≤ 0" << std::endl;
    
    // Test gradient boundary
    Real grad_boundary = Barrier::compute_gradient(g_max, g_max, k);
    assert(grad_boundary == 0.0);
    std::cout << "  ✓ dV/dg=0 at g = ḡ" << std::endl;
}

/**
 * Test C² smoothness at boundary g = ḡ
 */
void test_barrier_smoothness() {
    std::cout << "\nTesting C² smoothness at g = ḡ..." << std::endl;
    
    Real g_max = 0.01;
    Real k = 1000.0;
    Real delta = 1e-6;
    
    // Check that gradient and Hessian approach zero as g → ḡ
    Real g_near_boundary = g_max - delta;
    
    Real grad_near = Barrier::compute_gradient(g_near_boundary, g_max, k);
    Real hess_near = Barrier::compute_hessian(g_near_boundary, g_max, k);
    
    std::cout << "  At g = ḡ - δ:" << std::endl;
    std::cout << "    dV/dg  = " << grad_near << std::endl;
    std::cout << "    d²V/dg² = " << hess_near << std::endl;
    
    // At boundary, both should be small (approaching zero)
    Real grad_at = Barrier::compute_gradient(g_max, g_max, k);
    Real hess_at = Barrier::compute_hessian(g_max, g_max, k);
    
    assert(grad_at == 0.0);
    assert(hess_at == 0.0);
    
    std::cout << "  At g = ḡ:" << std::endl;
    std::cout << "    dV/dg  = " << grad_at << std::endl;
    std::cout << "    d²V/dg² = " << hess_at << std::endl;
    std::cout << "  ✓ C² continuity verified" << std::endl;
}

/**
 * Test sign conventions: force should be repulsive (gradient < 0 for g < ḡ)
 */
void test_barrier_force_direction() {
    std::cout << "\nTesting barrier force direction (repulsive)..." << std::endl;
    
    Real g_max = 0.01;
    Real k = 1000.0;
    
    // Inside barrier domain
    Real g1 = 0.002;  // 2mm (close)
    Real g2 = 0.005;  // 5mm (mid)
    Real g3 = 0.009;  // 9mm (near boundary)
    
    Real grad1 = Barrier::compute_gradient(g1, g_max, k);
    Real grad2 = Barrier::compute_gradient(g2, g_max, k);
    Real grad3 = Barrier::compute_gradient(g3, g_max, k);
    
    std::cout << "  dV/dg at g=2mm: " << grad1 << std::endl;
    std::cout << "  dV/dg at g=5mm: " << grad2 << std::endl;
    std::cout << "  dV/dg at g=9mm: " << grad3 << std::endl;
    
    // Gradient should be negative (repulsive force F = -dV/dg)
    assert(grad1 < 0.0);
    assert(grad2 < 0.0);
    assert(grad3 < 0.0);
    
    // Force magnitude should increase as gap decreases
    assert(std::abs(grad1) > std::abs(grad2));
    assert(std::abs(grad2) > std::abs(grad3));
    
    std::cout << "  ✓ Force is repulsive and increases with proximity" << std::endl;
}

/**
 * Test multiple gap values for consistency
 */
void test_barrier_consistency() {
    std::cout << "\nTesting barrier consistency across gap range..." << std::endl;
    
    Real g_max = 0.01;
    Real k = 1000.0;
    
    int num_tests = 10;
    Real max_rel_error = 0.0;
    
    for (int i = 1; i < num_tests; ++i) {
        Real g = (i / static_cast<Real>(num_tests)) * g_max;
        
        // Check gradient
        Real grad_analytic = Barrier::compute_gradient(g, g_max, k);
        Real V_plus = Barrier::compute_energy(g + EPSILON, g_max, k);
        Real V_minus = Barrier::compute_energy(g - EPSILON, g_max, k);
        Real grad_numeric = (V_plus - V_minus) / (2.0 * EPSILON);
        
        Real error = std::abs(grad_analytic - grad_numeric);
        Real rel_error = error / (std::abs(grad_numeric) + 1e-10);
        
        max_rel_error = std::max(max_rel_error, rel_error);
        
        if (rel_error > TOLERANCE) {
            std::cout << "  FAILED at g=" << g << ": rel_error=" << rel_error << std::endl;
            assert(false);
        }
    }
    
    std::cout << "  Max rel error across " << num_tests << " gaps: " 
              << max_rel_error * 100 << "%" << std::endl;
    std::cout << "  ✓ Consistent across gap range" << std::endl;
}

int main() {
    std::cout << std::setprecision(6) << std::fixed;
    std::cout << "\n========================================" << std::endl;
    std::cout << "Barrier Function Derivative Validation" << std::endl;
    std::cout << "========================================" << std::endl;
    
    test_barrier_energy_formula();
    test_barrier_gradient_numeric();
    test_barrier_hessian_numeric();
    test_barrier_domain();
    test_barrier_smoothness();
    test_barrier_force_direction();
    test_barrier_consistency();
    
    std::cout << "\n========================================" << std::endl;
    std::cout << "✓ All barrier derivative tests passed!" << std::endl;
    std::cout << "========================================\n" << std::endl;
    
    return 0;
}
