#include <cmath>
#include <iostream>

#include "integrator.h"
#include "mesh.h"
#include "state.h"

using namespace ando_barrier;

static State make_state_with_velocity(Real speed) {
    std::vector<Vec3> vertices = {
        Vec3(0.0, 0.0, 0.0), Vec3(0.1, 0.0, 0.0), Vec3(0.0, 0.1, 0.0)};
    std::vector<Triangle> triangles = {Triangle(0, 1, 2)};
    Material material;
    Mesh mesh;
    mesh.initialize(vertices, triangles, material);
    State state;
    state.initialize(mesh);
    for (auto& velocity : state.velocities) {
        velocity = Vec3(speed, 0.0, 0.0);
    }
    return state;
}

int main() {
    // Damping is a per-second rate: the velocity left after t seconds must be
    // exp(-rate * t) of the initial velocity, whatever the substep size.
    const Real rate = 0.05;
    const Real initial = 4.0;

    State one_step = make_state_with_velocity(initial);
    Integrator::apply_velocity_damping(one_step, rate, Real(1.0));

    State many_steps = make_state_with_velocity(initial);
    for (int i = 0; i < 1000; ++i) {
        Integrator::apply_velocity_damping(many_steps, rate, Real(0.001));
    }

    const Real expected = initial * std::exp(-rate);
    const Real one = one_step.velocities[0][0];
    const Real many = many_steps.velocities[0][0];
    std::cout << "after 1s one step=" << one << " 1000 steps=" << many
              << " expected=" << expected << std::endl;

    if (std::abs(one - expected) > Real(1e-9)) {
        std::cerr << "damping does not follow exp(-rate*t)\n";
        return 1;
    }
    if (std::abs(many - expected) > Real(1e-3)) {
        std::cerr << "damping depends on substep size\n";
        return 1;
    }

    State off = make_state_with_velocity(initial);
    Integrator::apply_velocity_damping(off, Real(0.0), Real(0.001));
    if (off.velocities[0][0] != initial) {
        std::cerr << "zero damping must not change velocity\n";
        return 1;
    }

    std::cout << "Velocity damping checks passed\n";
    return 0;
}
