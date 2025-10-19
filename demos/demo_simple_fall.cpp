/**
 * Basic gravity test using forward Euler integration
 * Demonstrates simple cloth falling with ground collision
 */

#include "demo_utils.h"
#include "../src/core/mesh.h"
#include "../src/core/state.h"
#include <iostream>

using namespace ando_barrier;
using namespace ando_barrier::demos;

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "Simple Gravity Test" << std::endl;
    std::cout << "========================================" << std::endl;
    
    // Material properties
    Material material;
    material.youngs_modulus = 1e5;
    material.poisson_ratio = 0.3;
    material.density = 200.0;
    material.thickness = 0.001;
    
    // Create cloth mesh
    std::vector<Vec3> vertices;
    std::vector<Triangle> triangles;
    SceneGenerator::create_cloth_mesh(
        1.0, 1.0,
        10, 10,
        0.0, 1.0, 0.0,  // Start at y=1.0
        vertices, triangles
    );
    
    std::cout << "Created mesh: " << vertices.size() << " vertices" << std::endl;
    std::cout << "Initial position of first vertex: " << vertices[0].transpose() << std::endl;
    
    Mesh mesh;
    mesh.initialize(vertices, triangles, material);
    
    State state;
    state.initialize(mesh);
    
    std::cout << "First vertex mass: " << state.masses[0] << " kg" << std::endl;
    
    // Forward Euler integration with gravity
    Real dt = 0.01;  // 10ms
    Vec3 gravity(0, -9.81, 0);
    
    for (int frame = 0; frame <= 100; ++frame) {
        if (frame % 10 == 0) {
            std::cout << "Frame " << frame << ": y = " << state.positions[50][1] << std::endl;
        }
        
        OBJExporter::export_sequence("output/simple_fall/frame", frame, mesh, state);
        
        // Update velocities and positions
        for (size_t i = 0; i < state.num_vertices(); ++i) {
            state.velocities[i] += gravity * dt;
            state.positions[i] += state.velocities[i] * dt;
            
            // Ground collision
            if (state.positions[i][1] < 0.0) {
                state.positions[i][1] = 0.0;
                state.velocities[i][1] = 0.0;
            }
        }
    }
    
    std::cout << "\n========================================" << std::endl;
    std::cout << "Test complete!" << std::endl;
    std::cout << "Final position of center vertex: " << state.positions[50].transpose() << std::endl;
    std::cout << "========================================" << std::endl;
    
    return 0;
}