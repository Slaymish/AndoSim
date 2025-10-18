/**
 * Demo 1: Cloth Draping onto Ground Plane
 * 
 * Demonstrates:
 * - Cloth mesh initialization
 * - Gravity forces
 * - Wall collision (ground plane at y=0)
 * - Pin constraints (top corners)
 * - Time integration with β accumulation
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
    std::cout << "Demo 1: Cloth Draping onto Ground" << std::endl;
    std::cout << "========================================" << std::endl;
    
    // Simulation parameters
    SimParams params;
    params.dt = 0.002;              // 2ms time step
    params.beta_max = 0.25;
    params.max_newton_steps = 8;
    params.pcg_tol = 1e-3;
    params.pcg_max_iters = 100;
    params.contact_gap_max = 0.001; // 1mm
    params.wall_gap = 0.001;
    
    // Material properties (soft cloth)
    Material material;
    material.youngs_modulus = 1e5;  // 100 kPa (soft)
    material.poisson_ratio = 0.3;
    material.density = 200.0;       // kg/m³ (light fabric)
    material.thickness = 0.001;     // 1mm
    
    // Create cloth mesh (1m × 1m, 20×20 resolution)
    std::vector<Vec3> vertices;
    std::vector<Triangle> triangles;
    SceneGenerator::create_cloth_mesh(
        1.0, 1.0,      // 1m × 1m
        20, 20,        // 20×20 vertices
        0.0, 0.5, 0.0, // Start at y=0.5m above ground
        vertices, triangles
    );
    
    std::cout << "Created cloth mesh: " << vertices.size() << " vertices, "
              << triangles.size() << " triangles" << std::endl;
    
    // Initialize mesh and state
    Mesh mesh;
    mesh.initialize(vertices, triangles, material);
    
    State state;
    state.initialize(mesh);
    
    std::cout << "Total mass: " << state.masses[0] * state.num_vertices() 
              << " kg" << std::endl;
    
    // Set up constraints
    Constraints constraints;
    
    // Pin top two corners
    int res_x = 20;
    int top_left = 0;
    int top_right = res_x - 1;
    
    constraints.add_pin(top_left, state.positions[top_left]);
    constraints.add_pin(top_right, state.positions[top_right]);
    
    std::cout << "Pinned corners: " << top_left << " and " << top_right << std::endl;
    
    // Add ground plane (y = 0, normal pointing up)
    Vec3 ground_normal(0, 1, 0);
    Real ground_offset = 0.0;
    constraints.add_wall(ground_normal, ground_offset, params.wall_gap);
    
    std::cout << "Added ground plane at y=0" << std::endl;
    
    // Add gravity
    Vec3 gravity(0, -9.81, 0);
    
    // Apply gravity to velocities (simple initialization)
    for (size_t i = 0; i < state.num_vertices(); ++i) {
        state.velocities[i] = gravity * params.dt;
    }
    
    // Simulation loop
    const int num_frames = 200;      // 200 frames
    const int steps_per_frame = 5;   // 5 steps per frame = 10ms per frame
    
    std::cout << "\nStarting simulation..." << std::endl;
    std::cout << "Total time: " << (num_frames * steps_per_frame * params.dt) 
              << " seconds" << std::endl;
    std::cout << "Output: output/cloth_drape/frame_XXXX.obj" << std::endl;
    
    auto start_time = std::chrono::high_resolution_clock::now();
    
    for (int frame = 0; frame <= num_frames; ++frame) {
        // Export frame
        if (frame % 10 == 0) {
            std::cout << "Frame " << frame << "/" << num_frames << std::endl;
        }
        OBJExporter::export_sequence("output/cloth_drape/frame", frame, mesh, state);
        
        // Simulate multiple steps per frame
        for (int step = 0; step < steps_per_frame; ++step) {
            // Apply gravity force (simple forward Euler for external forces)
            for (size_t i = 0; i < state.num_vertices(); ++i) {
                // Skip pinned vertices
                bool is_pinned = (i == static_cast<size_t>(top_left) || 
                                 i == static_cast<size_t>(top_right));
                if (!is_pinned) {
                    state.velocities[i] += gravity * params.dt;
                }
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
    
    std::cout << "\nTo visualize:" << std::endl;
    std::cout << "  1. Install Blender or MeshLab" << std::endl;
    std::cout << "  2. Load sequence: output/cloth_drape/frame_*.obj" << std::endl;
    std::cout << "  3. Or use the provided Python viewer (see demos/README.md)" << std::endl;
    
    return 0;
}
