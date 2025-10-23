#pragma once

#include "types.h"
#include "mesh.h"
#include "state.h"
#include <array>
#include <memory>
#include <vector>

namespace ando_barrier {

class RigidBody;

// Axis-aligned bounding box
struct AABB {
    Vec3 min;
    Vec3 max;
    
    AABB() : min(Vec3::Constant(std::numeric_limits<Real>::max())),
             max(Vec3::Constant(-std::numeric_limits<Real>::max())) {}
    
    AABB(const Vec3& min_, const Vec3& max_) : min(min_), max(max_) {}
    
    // Expand to include point
    void expand(const Vec3& p) {
        min = min.cwiseMin(p);
        max = max.cwiseMax(p);
    }
    
    // Expand to include another AABB
    void expand(const AABB& other) {
        min = min.cwiseMin(other.min);
        max = max.cwiseMax(other.max);
    }
    
    // Check if two AABBs overlap
    bool overlaps(const AABB& other) const {
        return (min[0] <= other.max[0] && max[0] >= other.min[0]) &&
               (min[1] <= other.max[1] && max[1] >= other.min[1]) &&
               (min[2] <= other.max[2] && max[2] >= other.min[2]);
    }
    
    // Get center point
    Vec3 center() const {
        return (min + max) * 0.5;
    }
    
    // Get longest axis (0=x, 1=y, 2=z)
    int longest_axis() const {
        Vec3 extent = max - min;
        if (extent[0] > extent[1] && extent[0] > extent[2]) return 0;
        if (extent[1] > extent[2]) return 1;
        return 2;
    }
};

// BVH node for spatial acceleration
struct BVHNode {
    AABB bbox;
    int left;       // Index of left child (-1 if leaf)
    int right;      // Index of right child (-1 if leaf)
    int prim_idx;   // Primitive index (triangle or edge) if leaf (-1 if internal)
    
    BVHNode() : left(-1), right(-1), prim_idx(-1) {}
    
    bool is_leaf() const { return prim_idx >= 0; }
};

// Contact types
enum class ContactType {
    POINT_TRIANGLE,        // Vertex vs triangle
    EDGE_EDGE,             // Edge vs edge
    WALL,                  // Vertex vs plane
    RIGID_POINT_TRIANGLE   // Vertex vs rigid triangle
};

// Contact pair from collision detection
struct ContactPair {
    ContactType type;

    // Indices (interpretation depends on type)
    // POINT_TRIANGLE: idx0 = vertex, idx1/2/3 = triangle vertices
    // EDGE_EDGE: idx0/1 = edge0 vertices, idx2/3 = edge1 vertices
    Index idx0, idx1, idx2, idx3;

    // Geometric data (computed in narrow phase)
    Real gap;           // Distance between primitives
    Vec3 normal;        // Contact normal (pointing from idx0 toward target)
    Vec3 witness_p;     // Witness point on primitive 0
    Vec3 witness_q;     // Witness point on primitive 1
    Vec3 barycentric;   // Barycentric coordinates for witness_q (triangle contacts)
    std::array<Real, 4> weights; // Extended direction weights W for each vertex
    int vertex_count;

    int rigid_body_index;

    ContactPair() : type(ContactType::POINT_TRIANGLE),
                   idx0(-1), idx1(-1), idx2(-1), idx3(-1),
                   gap(0.0), barycentric(Vec3::Zero()), vertex_count(0),
                   rigid_body_index(-1) {
        weights.fill(static_cast<Real>(0));
    }
};

// Collision detection system
class Collision {
public:
    // Build BVH from mesh triangles
    static void build_triangle_bvh(const Mesh& mesh, const State& state,
                                   std::vector<BVHNode>& nodes, std::vector<int>& prim_indices);
    
    // Build BVH from mesh edges
    static void build_edge_bvh(const Mesh& mesh, const State& state,
                              std::vector<BVHNode>& nodes, std::vector<int>& prim_indices);
    
    // Broad phase: find potential contact pairs using BVH
    static void broad_phase_triangles(const Mesh& mesh, const State& state,
                                     const std::vector<BVHNode>& bvh,
                                     std::vector<ContactPair>& candidates);
    
    static void broad_phase_edges(const Mesh& mesh, const State& state,
                                 const std::vector<BVHNode>& tri_bvh,
                                 const std::vector<BVHNode>& edge_bvh,
                                 std::vector<ContactPair>& candidates);
    
    // Narrow phase: compute exact distance and witness points
    static bool narrow_phase_point_triangle(const Vec3& p, 
                                           const Vec3& a, const Vec3& b, const Vec3& c,
                                           Real& distance, Vec3& normal,
                                           Vec3& witness_p, Vec3& witness_q);
    
    static bool narrow_phase_edge_edge(const Vec3& p0, const Vec3& p1,
                                      const Vec3& q0, const Vec3& q1,
                                      Real& distance, Vec3& normal,
                                      Vec3& witness_p, Vec3& witness_q);
    
    // Wall collision
    static void detect_wall_collisions(const State& state,
                                      const Vec3& plane_normal,
                                      Real plane_offset,
                                      std::vector<ContactPair>& contacts);
    
    // Full collision detection pipeline
    static void detect_all_collisions(const Mesh& mesh, const State& state,
                                     std::vector<ContactPair>& contacts);

    static void detect_all_collisions(const Mesh& mesh, const State& state,
                                      const std::vector<RigidBody>& rigids,
                                      std::vector<ContactPair>& contacts);

private:
    // Helper: build BVH recursively
    static int build_bvh_recursive(std::vector<BVHNode>& nodes,
                                  std::vector<AABB>& prim_boxes,
                                  std::vector<int>& prim_indices,
                                  int start, int end);
    
    // Helper: traverse two BVHs for overlap detection
    static void traverse_bvh_pair(const std::vector<BVHNode>& bvh1,
                                 const std::vector<BVHNode>& bvh2,
                                 int node1, int node2,
                                 std::vector<std::pair<int, int>>& overlaps);
};

} // namespace ando_barrier
