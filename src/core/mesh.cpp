#include "mesh.h"
#include <unordered_set>
#include <algorithm>
#include <cmath>

namespace ando_barrier {

void Mesh::initialize(const std::vector<Vec3>& verts,
                     const std::vector<Triangle>& tris,
                     const Material& mat) {
    vertices = verts;
    triangles = tris;
    material = mat;
    
    compute_rest_state();
}

void Mesh::compute_rest_state() {
    compute_edges();
    build_topology();
    
    // Compute per-face rest data
    Dm_inv.resize(triangles.size());
    rest_areas.resize(triangles.size());
    
    for (size_t i = 0; i < triangles.size(); ++i) {
        const Triangle& tri = triangles[i];
        const Vec3& v0 = vertices[tri.v[0]];
        const Vec3& v1 = vertices[tri.v[1]];
        const Vec3& v2 = vertices[tri.v[2]];

        // Edge vectors
        Vec3 e1 = v1 - v0;
        Vec3 e2 = v2 - v0;

        const Real eps = static_cast<Real>(1e-12);
        Real e1_len_sq = e1.squaredNorm();
        Real e2_len_sq = e2.squaredNorm();

        // Guard against degenerate triangles (zero area or duplicated vertices)
        if (e1_len_sq < eps || e2_len_sq < eps) {
            rest_areas[i] = static_cast<Real>(0.0);
            Dm_inv[i] = Mat2::Zero();
            continue;
        }

        // Compute local 2D basis
        Vec3 n = e1.cross(e2);
        Real normal_len = n.norm();

        if (normal_len < eps) {
            // e1 and e2 are nearly collinear → treat as degenerate face
            rest_areas[i] = static_cast<Real>(0.0);
            Dm_inv[i] = Mat2::Zero();
            continue;
        }

        Real area = normal_len * static_cast<Real>(0.5);
        rest_areas[i] = area;

        Vec3 n_unit = n / normal_len;
        Vec3 t1 = e1 / std::sqrt(e1_len_sq);
        Vec3 t2 = n_unit.cross(t1);

        // Project edges to 2D
        Mat2 Dm;
        Dm(0, 0) = e1.dot(t1);
        Dm(1, 0) = e1.dot(t2);
        Dm(0, 1) = e2.dot(t1);
        Dm(1, 1) = e2.dot(t2);

        // Invert for rest-state matrix (safe since we filtered degeneracies)
        Dm_inv[i] = Dm.inverse();
    }
}

void Mesh::compute_edges() {
    std::unordered_set<uint64_t> edge_set;
    edges.clear();
    
    auto make_edge_key = [](Index i, Index j) -> uint64_t {
        if (i > j) std::swap(i, j);
        return (uint64_t(i) << 32) | uint64_t(j);
    };
    
    // Extract unique edges from triangles
    for (const Triangle& tri : triangles) {
        for (int i = 0; i < 3; ++i) {
            Index v0 = tri.v[i];
            Index v1 = tri.v[(i + 1) % 3];
            uint64_t key = make_edge_key(v0, v1);
            
            if (edge_set.insert(key).second) {
                edges.push_back(Edge(v0 < v1 ? v0 : v1, v0 < v1 ? v1 : v0));
            }
        }
    }
}

void Mesh::build_topology() {
    vertex_to_faces.clear();
    vertex_to_faces.resize(vertices.size());
    vertex_to_edges.clear();
    vertex_to_edges.resize(vertices.size());
    
    // Build vertex-to-face connectivity
    for (size_t i = 0; i < triangles.size(); ++i) {
        const Triangle& tri = triangles[i];
        for (int j = 0; j < 3; ++j) {
            vertex_to_faces[tri.v[j]].push_back(i);
        }
    }
    
    // Build vertex-to-edge connectivity
    for (size_t i = 0; i < edges.size(); ++i) {
        const Edge& edge = edges[i];
        vertex_to_edges[edge.v[0]].push_back(i);
        vertex_to_edges[edge.v[1]].push_back(i);
    }
}

void Mesh::set_positions(const std::vector<Vec3>& new_positions) {
    vertices = new_positions;
}

Mat2 Mesh::compute_F(Index face_idx) const {
    const Triangle& tri = triangles[face_idx];
    const Vec3& v0 = vertices[tri.v[0]];
    const Vec3& v1 = vertices[tri.v[1]];
    const Vec3& v2 = vertices[tri.v[2]];
    
    // Edge vectors (deformed)
    Vec3 e1 = v1 - v0;
    Vec3 e2 = v2 - v0;
    
    // Compute local 2D basis (same as rest)
    Vec3 n = e1.cross(e2);
    n.normalize();
    Vec3 t1 = e1.normalized();
    Vec3 t2 = n.cross(t1);
    
    // Project edges to 2D
    Mat2 Ds;
    Ds(0, 0) = e1.dot(t1);
    Ds(1, 0) = e1.dot(t2);
    Ds(0, 1) = e2.dot(t1);
    Ds(1, 1) = e2.dot(t2);
    
    // F = Ds * Dm^{-1}
    return Ds * Dm_inv[face_idx];
}

} // namespace ando_barrier
