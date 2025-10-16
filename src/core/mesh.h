#pragma once

#include "types.h"
#include <vector>

namespace ando_barrier {

// Shell/cloth mesh representation
class Mesh {
public:
    // Geometry
    std::vector<Vec3> vertices;         // Current positions (N×3)
    std::vector<Triangle> triangles;    // Face connectivity (M×3)
    std::vector<Edge> edges;            // Edge connectivity for bending
    
    // Rest-state data
    std::vector<Mat2> Dm_inv;           // Per-face inverse rest-shape matrix
    std::vector<Real> rest_areas;       // Per-face rest areas
    
    // Topology
    std::vector<std::vector<Index>> vertex_to_faces;  // Incident faces per vertex
    std::vector<std::vector<Index>> vertex_to_edges;  // Incident edges per vertex
    
    // Material
    Material material;
    
    Mesh() = default;
    
    // Initialize from vertex positions and triangle indices
    void initialize(const std::vector<Vec3>& verts,
                   const std::vector<Triangle>& tris,
                   const Material& mat);
    
    // Compute rest-state data (Dm_inv, areas, topology)
    void compute_rest_state();
    
    // Update vertex positions
    void set_positions(const std::vector<Vec3>& new_positions);
    
    // Access
    size_t num_vertices() const { return vertices.size(); }
    size_t num_triangles() const { return triangles.size(); }
    size_t num_edges() const { return edges.size(); }
    
    // Compute deformation gradient for a face
    Mat2 compute_F(Index face_idx) const;
    
private:
    void build_topology();
    void compute_edges();
};

} // namespace ando_barrier
