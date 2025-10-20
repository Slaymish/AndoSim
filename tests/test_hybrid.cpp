#include <cassert>
#include <iostream>

#include "mesh.h"
#include "state.h"
#include "constraints.h"
#include "integrator.h"
#include "rigid_body.h"

using namespace ando_barrier;

int main() {
    // Simple cloth triangle positioned above the origin
    std::vector<Vec3> verts = {
        Vec3(0.0, 0.0, 0.02),
        Vec3(0.01, 0.0, 0.02),
        Vec3(0.0, 0.01, 0.02)
    };
    std::vector<Triangle> tris = { Triangle(0, 1, 2) };

    Material mat;
    mat.youngs_modulus = 1e5f;
    mat.thickness = 0.001f;

    Mesh mesh;
    mesh.initialize(verts, tris, mat);

    State state;
    state.initialize(mesh);

    // Give the first vertex a downward velocity toward the rigid plate
    state.velocities[0] = Vec3(0.0, 0.0, -0.5);

    Constraints constraints;

    // Create a rigid triangle acting as a ground plane
    std::vector<Vec3> rigid_verts = {
        Vec3(-0.05, -0.05, 0.0),
        Vec3(0.05, -0.05, 0.0),
        Vec3(-0.05, 0.05, 0.0)
    };
    std::vector<Triangle> rigid_tris = { Triangle(0, 1, 2) };

    RigidBody body;
    body.initialize(rigid_verts, rigid_tris, Real(1000.0));

    std::vector<RigidBody> bodies;
    bodies.push_back(body);

    SimParams params;
    params.dt = 0.01f;
    params.contact_gap_max = 0.05f;
    params.beta_max = 0.25f;
    params.pcg_tol = 1e-4f;
    params.max_newton_steps = 5;

    Integrator::step(mesh, state, constraints, params, &bodies);

    // The rigid body should now have some velocity induced by the cloth contact
    Vec3 rigid_velocity = bodies[0].linear_velocity();
    std::cout << "Rigid velocity: " << rigid_velocity.transpose() << std::endl;
    assert(rigid_velocity.norm() > Real(1e-6));

    // Cloth vertex velocity should have changed direction (contact response)
    Vec3 cloth_velocity = state.velocities[0];
    std::cout << "Cloth vertex velocity: " << cloth_velocity.transpose() << std::endl;
    assert(cloth_velocity[2] > -0.5f);

    return 0;
}

