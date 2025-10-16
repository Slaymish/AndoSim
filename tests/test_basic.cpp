#include "../src/core/types.h"
#include "../src/core/barrier.h"
#include "../src/core/mesh.h"
#include "../src/core/state.h"
#include "../src/core/elasticity.h"
#include "../src/core/stiffness.h"
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

int main() {
    std::cout << "\n========= Stiffness Tests =========\n" << std::endl;
    test_stiffness_contact();
    test_stiffness_pin();
    test_stiffness_takeover();
    std::cout << "\n========= All Tests Passed =========\n" << std::endl;
    return 0;
}
