#include <cassert>
#include <cmath>
#include <iostream>
#include <string>

#include "mesh.h"
#include "state.h"
#include "constraints.h"
#include "integrator.h"
#include "rigid_body.h"
#include "line_search.h"

using namespace ando_barrier;

int main(int argc, char** argv) {
    if (argc == 2 && (std::string(argv[1]) == "--sphere-crossing" ||
                      std::string(argv[1]) == "--sphere-hold" ||
                      std::string(argv[1]) == "--sphere-face")) {
        const bool hold = std::string(argv[1]) == "--sphere-hold";
        // A small cloth patch starts outside an octahedral unit sphere, beyond
        // the detection range, and attempts to cross its top in one step.
        // The gravity variant also checks one second of contact and sliding.
        Mesh mesh;
        Material mat;
        const bool face = std::string(argv[1]) == "--sphere-face";
        const std::vector<Vec3> verts = face
            ? std::vector<Vec3>{Vec3(-2,-2,1.2),Vec3(2,-2,1.2),Vec3(0,2,1.2)}
            : hold ? std::vector<Vec3>{Vec3(-.02,-.011547,1.2),Vec3(.02,-.011547,1.2),Vec3(0,.023094,1.2)}
            : std::vector<Vec3>{Vec3(0,0,1.2), Vec3(.02,0,1.2), Vec3(0,.02,1.2)};
        mesh.initialize(verts,
                        {Triangle(0,1,2)}, mat);
        State state;
        state.initialize(mesh);
        for (auto& v : state.velocities) v = hold ? Vec3::Zero() : Vec3(0,0,-400);
        RigidBody sphere;
        sphere.initialize({Vec3(0,0,1),Vec3(1,0,0),Vec3(0,1,0),
                           Vec3(-1,0,0),Vec3(0,-1,0),Vec3(0,0,-1)},
                          {Triangle(0,1,2),Triangle(0,2,3),Triangle(0,3,4),Triangle(0,4,1),
                           Triangle(5,2,1),Triangle(5,3,2),Triangle(5,4,3),Triangle(5,1,4)}, 1e12);
        std::vector<RigidBody> bodies{sphere};
        Constraints constraints;
        SimParams params;
        params.dt=.01; params.contact_gap_max=.02;
        params.enable_friction=false; params.enable_strain_limiting=false;
        params.dt = hold ? Real(.002) : Real(.01);
        params.pcg_tol = Real(1e-6);
        Real minimum_gap = 100;
        int contact_steps = 0;
        const int steps = hold ? 500 : 1;
        for (int step=0; step<steps; ++step) {
            if (hold) for (auto& v : state.velocities) v[2] -= Real(9.81)*params.dt;
            Integrator::step(mesh, state, constraints, params, &bodies);
            auto contacts = Integrator::compute_contacts(mesh,state,&bodies,params.contact_gap_max);
            if (!contacts.empty()) ++contact_steps;
            for (const auto& p : state.positions) {
                Real gap = (std::abs(p[2]) - 1 + std::abs(p[0]) + std::abs(p[1])) / std::sqrt(Real(3));
                minimum_gap = std::min(minimum_gap,gap);
                if (!p.allFinite() || gap < 0) {
                    std::cerr << "FAIL: sphere clearance=" << gap << " step=" << step << " p=" << p.transpose() << " body=" << bodies[0].position().transpose() << "\n";
                    return 1;
                }
            }
        }
        if (face && state.positions[0][2] < Real(1)) {
            std::cerr << "FAIL: sphere pierced cloth face with all cloth vertices outside\n";
            return 1;
        }
        std::cout << "minimum face clearance=" << minimum_gap << " contact steps=" << contact_steps << std::endl;
        if (hold && (contact_steps < 100 || state.positions[0][2] > Real(1.15))) return 1;
        for (const auto& p : state.positions) {
            std::cout << "sphere crossing result " << p.transpose() << std::endl;
            if (!p.allFinite() || (!hold && p[2] < 1 - std::abs(p[0]) - std::abs(p[1]))) {
                std::cerr << "FAIL: cloth crossed the rigid sphere surface\n";
                return 1;
            }
        }
        return 0;
    }
    if (argc == 2 && std::string(argv[1]) == "--rigid-edge") {
        Mesh mesh; Material mat;
        mesh.initialize({Vec3(-1,0,.001),Vec3(1,0,.001),Vec3(-1,.02,.001)},
                        {Triangle(0,1,2)},mat);
        State state; state.initialize(mesh);
        RigidBody body;
        body.initialize({Vec3(0,-1,0),Vec3(0,1,0),Vec3(0,0,-2)},
                        {Triangle(0,1,2)},1e12);
        std::vector<RigidBody> bodies{body};
        std::vector<ContactPair> contacts;
        Collision::detect_all_collisions(mesh,state,bodies,contacts,Real(.01));
        bool edge=false;
        for (const auto& c : contacts) if (c.vertex_count==2) edge=true;
        VecX direction=VecX::Zero(9);
        for (int i=0;i<3;++i) direction[3*i+2]=Real(-.01);
        Real alpha=LineSearch::search(mesh,state,direction,{}, {},Vec3::Zero(),0,1,1e-6,&bodies);
        std::cout << "rigid edge contact=" << edge << " alpha=" << alpha << std::endl;
        return edge && alpha > 0 && alpha < Real(.1) ? 0 : 1;
    }
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

    if (argc == 2 && (std::string(argv[1]) == "--rigid-force-only" ||
                      std::string(argv[1]) == "--barrier-range-force-only")) {
        // Isolate rigid force accumulation from Newton motion: an active contact
        // above the plate must push the plate down, opposite the cloth force.
        State force_state = state;
        for (auto& position : force_state.positions) {
            // Keep projections strictly inside the rigid triangle.
            position[0] -= Real(0.01);
            position[1] -= Real(0.01);
            position[2] = std::string(argv[1]) == "--barrier-range-force-only"
                ? Real(0.02) : Real(0.005);
        }
        auto force_bodies = bodies;
        SimParams force_params = params;
        force_params.max_newton_steps = 0;
        Integrator::step(mesh, force_state, constraints, force_params, &force_bodies);
        std::cout << "Rigid contact force probe velocity: "
                  << force_bodies[0].linear_velocity().transpose() << std::endl;
        const Vec3 velocity = force_bodies[0].linear_velocity();
        assert(velocity[2] < Real(0));
        assert(std::abs(velocity[0]) < Real(1e-5));
        assert(std::abs(velocity[1]) < Real(1e-5));
        return 0;
    }

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

