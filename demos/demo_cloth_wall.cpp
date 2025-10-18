/**
 * Demo 2: Cloth Collision with Wall
 * 
 * Demonstrates:
 * - Cloth falling and hitting a wall
 * - Wall collision detection and response
 * - Contact constraints
 * - Dynamic behavior without pins
 */

#include "demo_utils.h"
#include "../src/core/integrator.h"
#include "../src/core/constraints.h"
#include <iostream>
#include <chrono>

using namespace ando_barrier;
using namespace ando_barrier::demos;

int main(int argc, char** argv) {
    std::cout << "========================================" << std::endl;
    std::cout << "Demo 2: Cloth Wall Collision" << std::endl;
    std::cout << "========================================" << std::endl;
    
    // Simulation parameters
    SimParams params;
    params.dt = 0.002;
    params.beta_max = 0.25;
    params.max_newton_steps = 8;
    params.pcg_tol = 1e-3;
    params.pcg_max_iters = 100;
    params.contact_gap_max = 0.001;
    params.wall_gap = 0.001;
    
    // Material properties
    Material material;
    material.youngs_modulus = 5e5;  // 500 kPa (stiffer)
    material.poisson_ratio = 0.3;
    material.density = 300.0;
    material.thickness = 0.001;
    
    // Create cloth mesh (0.5m × 0.5m, 15×15 resolution)
    // Start horizontally at z = 2.0m, will fall toward wall at z = 0
    std::vector<Vec3> vertices;
    std::vector<Triangle> triangles;
    
    const int res = 15;
    SceneGenerator::create_cloth_mesh(
        0.5, 0.5,      // 0.5m × 0.5m
        res, res,      // 15×15 vertices
        0.0, 0.5, 1.5, // Start at z=1.5m from wall
        vertices, triangles
    );
    
    // Rotate cloth to be vertical (facing the wall)
    for (auto& v : vertices) {
        Real y = v[1];
        Real z = v[2];
        v[1] = z - 0.5;  // Rotate to make vertical
        v[2] = y;
    }
    
    std::cout << "Created cloth mesh: " << vertices.size() << " vertices, "
              << triangles.size() << " triangles" << std::endl;
    
    // Initialize mesh and state
    Mesh mesh;
    mesh.initialize(vertices, triangles, material);
    
    State state;
    state.initialize(mesh);
    
    // Set up constraints
    Constraints constraints;
    
    // Add wall at z = 0, normal pointing in +z direction
    Vec3 wall_normal(0, 0, 1);
    Real wall_offset = 0.0;
    constraints.add_wall(wall_normal, wall_offset, params.wall_gap);
    
    // Add floor at y = 0
    Vec3 floor_normal(0, 1, 0);
    Real floor_offset = 0.0;
    constraints.add_wall(floor_normal, floor_offset, params.wall_gap);
    
    std::cout << "Added wall at z=0 and floor at y=0" << std::endl;
    
    // Initial velocity: push cloth toward wall
    Vec3 initial_velocity(0, 0, -2.0);  // 2 m/s toward wall
    Vec3 gravity(0, -9.81, 0);
    
    for (size_t i = 0; i < state.num_vertices(); ++i) {
        state.velocities[i] = initial_velocity;
    }
    
    std::cout << "Initial velocity: " << initial_velocity.transpose() << " m/s" << std::endl;
    
    // Simulation loop
    const int num_frames = 250;
    const int steps_per_frame = 5;
    
    std::cout << "\nStarting simulation..." << std::endl;
    std::cout << "Total time: " << (num_frames * steps_per_frame * params.dt) 
              << " seconds" << std::endl;
    std::cout << "Output: output/cloth_wall/frame_XXXX.obj" << std::endl;
    
    auto start_time = std::chrono::high_resolution_clock::now();
    
    for (int frame = 0; frame <= num_frames; ++frame) {
        if (frame % 10 == 0) {
            // Report min z position (distance from wall)
            Real min_z = 1e6;
            for (const auto& pos : state.positions) {
                min_z = std::min(min_z, pos[2]);
            }
            std::cout << "Frame " << frame << "/" << num_frames 
                      << " - Min Z: " << min_z << " m" << std::endl;
        }
        
        OBJExporter::export_sequence("output/cloth_wall/frame", frame, mesh, state);
        
        // Simulate
        for (int step = 0; step < steps_per_frame; ++step) {
            // Apply gravity
            for (size_t i = 0; i < state.num_vertices(); ++i) {
                state.velocities[i] += gravity * params.dt;
            }
            
            // Take physics step
            Integrator::step(mesh, state, constraints, params);
        }
    }
    
    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(
        end_time - start_time
    );
    
    std::cout << "\n========================================" << std::endl;
    std::cout << "Simulation complete!" << std::endl;
    std::cout << "Total time: " << duration.count() << " ms" << std::endl;
    std::cout << "FPS: " << (num_frames * 1000.0 / duration.count()) << std::endl;
    std::cout << "========================================" << std::endl;
    
    return 0;
}
