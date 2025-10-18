#pragma once

#include "../src/core/types.h"
#include "../src/core/mesh.h"
#include "../src/core/state.h"
#include <string>
#include <fstream>
#include <iostream>
#include <filesystem>
#include <system_error>

namespace ando_barrier {
namespace demos {

namespace detail {

inline void ensure_parent_directory(const std::string& filename) {
    namespace fs = std::filesystem;
    std::error_code ec;
    fs::path path(filename);
    fs::path parent = path.has_filename() ? path.parent_path() : path;
    if (!parent.empty()) {
        fs::create_directories(parent, ec);
        if (ec) {
            std::cerr << "Warning: failed to create directory " << parent
                      << " (" << ec.message() << ")" << std::endl;
        }
    }
}

} // namespace detail

/**
 * Simple OBJ file exporter for visualization
 * Outputs mesh at each frame as separate .obj file
 */
class OBJExporter {
public:
    /**
     * Export mesh to OBJ file
     * 
     * @param filename Output filename (e.g., "frame_0001.obj")
     * @param mesh Mesh topology
     * @param state Current state (positions)
     */
    static void export_frame(const std::string& filename, 
                            const Mesh& mesh, 
                            const State& state) {
        detail::ensure_parent_directory(filename);

        std::ofstream file(filename);
        if (!file.is_open()) {
            std::cerr << "Failed to open " << filename << std::endl;
            return;
        }
        
        // Write vertices
        for (size_t i = 0; i < state.positions.size(); ++i) {
            const Vec3& v = state.positions[i];
            file << "v " << v[0] << " " << v[1] << " " << v[2] << "\n";
        }
        
        // Write faces (1-indexed in OBJ format)
        for (const auto& tri : mesh.triangles) {
            file << "f " << (tri.v[0] + 1) << " " 
                 << (tri.v[1] + 1) << " " 
                 << (tri.v[2] + 1) << "\n";
        }
        
        file.close();
    }
    
    /**
     * Export sequence with frame number formatting
     * 
     * @param base_name Base name (e.g., "cloth_drape")
     * @param frame Frame number
     * @param mesh Mesh topology
     * @param state Current state
     */
    static void export_sequence(const std::string& base_name,
                               int frame,
                               const Mesh& mesh,
                               const State& state) {
        char filename[256];
        snprintf(filename, sizeof(filename), "%s_%04d.obj", 
                base_name.c_str(), frame);
        export_frame(filename, mesh, state);
    }
};

/**
 * Scene generator utilities
 */
class SceneGenerator {
public:
    /**
     * Create a rectangular cloth mesh
     * 
     * @param width Width in world units (X direction)
     * @param depth Depth in world units (Z direction)
     * @param res_x Number of vertices in x direction
     * @param res_z Number of vertices in z direction
     * @param center_x Center position x
     * @param center_y Center position y (height)
     * @param center_z Center position z
     * @param vertices Output vertex positions
     * @param triangles Output triangle indices
     */
    static void create_cloth_mesh(
        Real width, Real depth,
        int res_x, int res_z,
        Real center_x, Real center_y, Real center_z,
        std::vector<Vec3>& vertices,
        std::vector<Triangle>& triangles) {
        
        vertices.clear();
        triangles.clear();
        
        // Generate grid vertices in XZ plane (Y is up)
        for (int j = 0; j < res_z; ++j) {
            for (int i = 0; i < res_x; ++i) {
                Real u = static_cast<Real>(i) / (res_x - 1);
                Real v = static_cast<Real>(j) / (res_z - 1);
                
                Real x = center_x + (u - 0.5) * width;
                Real y = center_y;  // Constant height (horizontal cloth)
                Real z = center_z + (v - 0.5) * depth;
                
                vertices.push_back(Vec3(x, y, z));
            }
        }
        
        // Generate triangles
        for (int j = 0; j < res_z - 1; ++j) {
            for (int i = 0; i < res_x - 1; ++i) {
                int v0 = j * res_x + i;
                int v1 = j * res_x + (i + 1);
                int v2 = (j + 1) * res_x + (i + 1);
                int v3 = (j + 1) * res_x + i;
                
                // Two triangles per quad
                triangles.push_back(Triangle(v0, v1, v2));
                triangles.push_back(Triangle(v0, v2, v3));
            }
        }
    }
    
    /**
     * Create a ground plane mesh
     * 
     * @param size Size of plane (width and depth)
     * @param resolution Number of subdivisions per side
     * @param height Y-coordinate of plane
     * @param vertices Output vertex positions
     * @param triangles Output triangle indices
     */
    static void create_ground_plane(
        Real size, int resolution, Real height,
        std::vector<Vec3>& vertices,
        std::vector<Triangle>& triangles) {
        
        create_cloth_mesh(size, size, resolution, resolution,
                         0.0, height, 0.0,
                         vertices, triangles);
    }
};

} // namespace demos
} // namespace ando_barrier
