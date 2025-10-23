#include "collision.h"
#include <algorithm>
#include <limits>

#include "rigid_body.h"

namespace ando_barrier {

namespace {

static Vec3 compute_triangle_barycentric(const Vec3& p, const Vec3& a,
                                         const Vec3& b, const Vec3& c) {
    Vec3 v0 = b - a;
    Vec3 v1 = c - a;
    Vec3 v2 = p - a;

    Real d00 = v0.dot(v0);
    Real d01 = v0.dot(v1);
    Real d11 = v1.dot(v1);
    Real d20 = v2.dot(v0);
    Real d21 = v2.dot(v1);

    Real denom = d00 * d11 - d01 * d01;
    Real v = Real(0.0);
    Real w = Real(0.0);
    if (std::abs(denom) > std::numeric_limits<Real>::epsilon()) {
        v = (d11 * d20 - d01 * d21) / denom;
        w = (d00 * d21 - d01 * d20) / denom;
    }

    v = std::clamp(v, Real(0.0), Real(1.0));
    w = std::clamp(w, Real(0.0), Real(1.0));
    if (v + w > Real(1.0)) {
        Real sum = v + w;
        if (sum > std::numeric_limits<Real>::epsilon()) {
            v /= sum;
            w /= sum;
        }
    }

    Real u = Real(1.0) - v - w;
    return Vec3(u, v, w);
}

} // namespace

// Build AABB for triangle
static AABB compute_triangle_aabb(const Vec3& a, const Vec3& b, const Vec3& c) {
    AABB box;
    box.expand(a);
    box.expand(b);
    box.expand(c);
    return box;
}

// Build AABB for edge
static AABB compute_edge_aabb(const Vec3& a, const Vec3& b) {
    AABB box;
    box.expand(a);
    box.expand(b);
    return box;
}

// Build BVH recursively using SAH (Surface Area Heuristic) split
int Collision::build_bvh_recursive(std::vector<BVHNode>& nodes,
                                   std::vector<AABB>& prim_boxes,
                                   std::vector<int>& prim_indices,
                                   int start, int end) {
    int node_idx = nodes.size();
    nodes.emplace_back();
    BVHNode& node = nodes[node_idx];
    
    // Compute bounding box for all primitives in range
    for (int i = start; i < end; ++i) {
        node.bbox.expand(prim_boxes[prim_indices[i]]);
    }
    
    int num_prims = end - start;
    
    // Leaf node if few primitives
    if (num_prims <= 4) {
        if (num_prims == 1) {
            node.prim_idx = prim_indices[start];
        }
        return node_idx;
    }
    
    // Find best split axis
    int axis = node.bbox.longest_axis();
    
    // Sort primitives by centroid along axis
    std::sort(prim_indices.begin() + start, prim_indices.begin() + end,
             [&](int a, int b) {
                 return prim_boxes[a].center()[axis] < prim_boxes[b].center()[axis];
             });
    
    // Split in middle
    int mid = start + num_prims / 2;
    
    // Recursively build children
    node.left = build_bvh_recursive(nodes, prim_boxes, prim_indices, start, mid);
    node.right = build_bvh_recursive(nodes, prim_boxes, prim_indices, mid, end);
    
    return node_idx;
}

// Build triangle BVH
void Collision::build_triangle_bvh(const Mesh& mesh, const State& state,
                                  std::vector<BVHNode>& nodes, 
                                  std::vector<int>& prim_indices) {
    nodes.clear();
    prim_indices.clear();
    
    if (mesh.triangles.empty()) return;
    
    // Compute AABB for each triangle
    std::vector<AABB> tri_boxes(mesh.triangles.size());
    for (size_t i = 0; i < mesh.triangles.size(); ++i) {
        const auto& tri = mesh.triangles[i];
        tri_boxes[i] = compute_triangle_aabb(state.positions[tri.v[0]], 
                                            state.positions[tri.v[1]], 
                                            state.positions[tri.v[2]]);
    }
    
    // Initialize primitive indices
    prim_indices.resize(mesh.triangles.size());
    for (size_t i = 0; i < prim_indices.size(); ++i) {
        prim_indices[i] = i;
    }
    
    // Build BVH
    build_bvh_recursive(nodes, tri_boxes, prim_indices, 0, prim_indices.size());
}

// Build edge BVH
void Collision::build_edge_bvh(const Mesh& mesh, const State& state,
                              std::vector<BVHNode>& nodes,
                              std::vector<int>& prim_indices) {
    nodes.clear();
    prim_indices.clear();
    
    if (mesh.edges.empty()) return;
    
    // Compute AABB for each edge
    std::vector<AABB> edge_boxes(mesh.edges.size());
    for (size_t i = 0; i < mesh.edges.size(); ++i) {
        const auto& edge = mesh.edges[i];
        edge_boxes[i] = compute_edge_aabb(state.positions[edge.v[0]], state.positions[edge.v[1]]);
    }
    
    // Initialize primitive indices
    prim_indices.resize(mesh.edges.size());
    for (size_t i = 0; i < prim_indices.size(); ++i) {
        prim_indices[i] = i;
    }
    
    // Build BVH
    build_bvh_recursive(nodes, edge_boxes, prim_indices, 0, prim_indices.size());
}

// Traverse BVH pair for overlaps
void Collision::traverse_bvh_pair(const std::vector<BVHNode>& bvh1,
                                 const std::vector<BVHNode>& bvh2,
                                 int node1_idx, int node2_idx,
                                 std::vector<std::pair<int, int>>& overlaps) {
    if (node1_idx < 0 || node2_idx < 0) return;
    if (bvh1.empty() || bvh2.empty()) return;
    
    const BVHNode& node1 = bvh1[node1_idx];
    const BVHNode& node2 = bvh2[node2_idx];
    
    // Check AABB overlap
    if (!node1.bbox.overlaps(node2.bbox)) return;
    
    // Both leaves - record overlap
    if (node1.is_leaf() && node2.is_leaf()) {
        overlaps.emplace_back(node1.prim_idx, node2.prim_idx);
        return;
    }
    
    // Recurse on larger node
    if (node1.is_leaf()) {
        traverse_bvh_pair(bvh1, bvh2, node1_idx, node2.left, overlaps);
        traverse_bvh_pair(bvh1, bvh2, node1_idx, node2.right, overlaps);
    } else if (node2.is_leaf()) {
        traverse_bvh_pair(bvh1, bvh2, node1.left, node2_idx, overlaps);
        traverse_bvh_pair(bvh1, bvh2, node1.right, node2_idx, overlaps);
    } else {
        // Both internal - recurse on all combinations
        traverse_bvh_pair(bvh1, bvh2, node1.left, node2.left, overlaps);
        traverse_bvh_pair(bvh1, bvh2, node1.left, node2.right, overlaps);
        traverse_bvh_pair(bvh1, bvh2, node1.right, node2.left, overlaps);
        traverse_bvh_pair(bvh1, bvh2, node1.right, node2.right, overlaps);
    }
}

// Broad phase for vertex-triangle
void Collision::broad_phase_triangles(const Mesh& mesh, const State& state,
                                     const std::vector<BVHNode>& bvh,
                                     std::vector<ContactPair>& candidates) {
    if (bvh.empty()) return;
    
    // For each vertex, find overlapping triangles
    for (size_t v = 0; v < state.positions.size(); ++v) {
        const Vec3& p = state.positions[v];
        
        // Create point AABB with small epsilon
        AABB point_box(p - Vec3::Constant(1e-4), p + Vec3::Constant(1e-4));
        
        // Traverse BVH to find overlapping triangles
        std::vector<int> overlapping_tris;
        std::function<void(int)> traverse = [&](int node_idx) {
            if (node_idx < 0 || node_idx >= (int)bvh.size()) return;
            const BVHNode& node = bvh[node_idx];
            
            if (!point_box.overlaps(node.bbox)) return;
            
            if (node.is_leaf()) {
                // Don't self-collide with adjacent triangles
                const auto& tri = mesh.triangles[node.prim_idx];
                if (tri.v[0] == (int)v || tri.v[1] == (int)v || tri.v[2] == (int)v) return;
                
                overlapping_tris.push_back(node.prim_idx);
            } else {
                traverse(node.left);
                traverse(node.right);
            }
        };
        
        traverse(0);
        
        // Create candidate pairs
        for (int tri_idx : overlapping_tris) {
            ContactPair pair;
            pair.type = ContactType::POINT_TRIANGLE;
            pair.idx0 = v;
            const auto& tri = mesh.triangles[tri_idx];
            pair.idx1 = tri.v[0];
            pair.idx2 = tri.v[1];
            pair.idx3 = tri.v[2];
            candidates.push_back(pair);
        }
    }
}

// Broad phase for edge-edge
void Collision::broad_phase_edges(const Mesh& mesh, const State& state,
                                 const std::vector<BVHNode>& tri_bvh,
                                 const std::vector<BVHNode>& edge_bvh,
                                 std::vector<ContactPair>& candidates) {
    if (edge_bvh.empty()) return;
    
    // Find overlapping edge pairs
    std::vector<std::pair<int, int>> overlaps;
    traverse_bvh_pair(edge_bvh, edge_bvh, 0, 0, overlaps);
    
    // Create candidate pairs
    for (const auto& [e1, e2] : overlaps) {
        if (e1 >= e2) continue;  // Avoid duplicates
        
        const auto& edge1 = mesh.edges[e1];
        const auto& edge2 = mesh.edges[e2];
        
        // Skip if edges share a vertex
        if (edge1.v[0] == edge2.v[0] || edge1.v[0] == edge2.v[1] ||
            edge1.v[1] == edge2.v[0] || edge1.v[1] == edge2.v[1]) continue;
        
        ContactPair pair;
        pair.type = ContactType::EDGE_EDGE;
        pair.idx0 = edge1.v[0];
        pair.idx1 = edge1.v[1];
        pair.idx2 = edge2.v[0];
        pair.idx3 = edge2.v[1];
        candidates.push_back(pair);
    }
}

// Point-triangle distance (closest point on triangle to point)
bool Collision::narrow_phase_point_triangle(const Vec3& p,
                                           const Vec3& a, const Vec3& b, const Vec3& c,
                                           Real& distance, Vec3& normal,
                                           Vec3& witness_p, Vec3& witness_q) {
    // Compute barycentric coordinates
    Vec3 ab = b - a;
    Vec3 ac = c - a;
    Vec3 ap = p - a;
    
    Real d1 = ab.dot(ap);
    Real d2 = ac.dot(ap);
    
    // Check vertex region A
    if (d1 <= 0.0 && d2 <= 0.0) {
        witness_q = a;
        witness_p = p;
        Vec3 diff = p - a;
        distance = diff.norm();
        normal = distance > 1e-10 ? diff / distance : Vec3(0, 0, 1);
        return true;
    }
    
    // Check edge AB
    Vec3 bp = p - b;
    Real d3 = ab.dot(bp);
    Real d4 = ac.dot(bp);
    if (d3 >= 0.0 && d4 <= d3) {
        witness_q = b;
        witness_p = p;
        Vec3 diff = p - b;
        distance = diff.norm();
        normal = distance > 1e-10 ? diff / distance : Vec3(0, 0, 1);
        return true;
    }
    
    // Check edge AC
    Vec3 cp = p - c;
    Real d5 = ab.dot(cp);
    Real d6 = ac.dot(cp);
    if (d6 >= 0.0 && d5 <= d6) {
        witness_q = c;
        witness_p = p;
        Vec3 diff = p - c;
        distance = diff.norm();
        normal = distance > 1e-10 ? diff / distance : Vec3(0, 0, 1);
        return true;
    }
    
    // Check if P in edge region of AB
    Real vc = d1 * d4 - d3 * d2;
    if (vc <= 0.0 && d1 >= 0.0 && d3 <= 0.0) {
        Real v = d1 / (d1 - d3);
        witness_q = a + v * ab;
        witness_p = p;
        Vec3 diff = p - witness_q;
        distance = diff.norm();
        normal = distance > 1e-10 ? diff / distance : Vec3(0, 0, 1);
        return true;
    }
    
    // Check if P in edge region of AC
    Real vb = d5 * d2 - d1 * d6;
    if (vb <= 0.0 && d2 >= 0.0 && d6 <= 0.0) {
        Real w = d2 / (d2 - d6);
        witness_q = a + w * ac;
        witness_p = p;
        Vec3 diff = p - witness_q;
        distance = diff.norm();
        normal = distance > 1e-10 ? diff / distance : Vec3(0, 0, 1);
        return true;
    }
    
    // Check if P in edge region of BC
    Real va = d3 * d6 - d5 * d4;
    if (va <= 0.0 && (d4 - d3) >= 0.0 && (d5 - d6) >= 0.0) {
        Real w = (d4 - d3) / ((d4 - d3) + (d5 - d6));
        witness_q = b + w * (c - b);
        witness_p = p;
        Vec3 diff = p - witness_q;
        distance = diff.norm();
        normal = distance > 1e-10 ? diff / distance : Vec3(0, 0, 1);
        return true;
    }
    
    // P inside face region
    Real denom = 1.0 / (va + vb + vc);
    Real v = vb * denom;
    Real w = vc * denom;
    witness_q = a + ab * v + ac * w;
    witness_p = p;
    
    Vec3 diff = p - witness_q;
    distance = diff.norm();
    
    // Use triangle normal if point is very close
    Vec3 tri_normal = ab.cross(ac);
    Real tri_area = tri_normal.norm();
    if (tri_area > 1e-10) {
        tri_normal /= tri_area;
        // Orient normal toward point
        if (tri_normal.dot(diff) < 0) tri_normal = -tri_normal;
        normal = tri_normal;
    } else {
        normal = distance > 1e-10 ? diff / distance : Vec3(0, 0, 1);
    }
    
    return true;
}

// Edge-edge distance (closest points on two line segments)
bool Collision::narrow_phase_edge_edge(const Vec3& p0, const Vec3& p1,
                                      const Vec3& q0, const Vec3& q1,
                                      Real& distance, Vec3& normal,
                                      Vec3& witness_p, Vec3& witness_q) {
    Vec3 d1 = p1 - p0;
    Vec3 d2 = q1 - q0;
    Vec3 r = p0 - q0;
    
    Real a = d1.dot(d1);
    Real e = d2.dot(d2);
    Real f = d2.dot(r);
    
    Real s, t;
    Real epsilon = 1e-10;
    
    if (a <= epsilon && e <= epsilon) {
        // Both segments degenerate to points
        s = t = 0.0;
        witness_p = p0;
        witness_q = q0;
    } else {
        if (a <= epsilon) {
            // First segment is a point
            s = 0.0;
            t = std::clamp(f / e, 0.0f, 1.0f);
        } else {
            Real c = d1.dot(r);
            if (e <= epsilon) {
                // Second segment is a point
                t = 0.0;
                s = std::clamp(-c / a, 0.0f, 1.0f);
            } else {
                // General case
                Real b = d1.dot(d2);
                Real denom = a * e - b * b;
                
                if (denom != 0.0) {
                    s = std::clamp((b * f - c * e) / denom, 0.0f, 1.0f);
                } else {
                    s = 0.0;
                }
                
                t = (b * s + f) / e;
                
                if (t < 0.0) {
                    t = 0.0;
                    s = std::clamp(-c / a, 0.0f, 1.0f);
                } else if (t > 1.0) {
                    t = 1.0;
                    s = std::clamp((b - c) / a, 0.0f, 1.0f);
                }
            }
        }
        
        witness_p = p0 + s * d1;
        witness_q = q0 + t * d2;
    }
    
    Vec3 diff = witness_p - witness_q;
    distance = diff.norm();
    normal = distance > 1e-10 ? diff / distance : Vec3(0, 0, 1);
    
    return true;
}

// Wall collision detection
void Collision::detect_wall_collisions(const State& state,
                                      const Vec3& plane_normal,
                                      Real plane_offset,
                                      std::vector<ContactPair>& contacts) {
    for (size_t i = 0; i < state.positions.size(); ++i) {
        Real signed_dist = plane_normal.dot(state.positions[i]) - plane_offset;
        
        if (signed_dist < 0.01) {  // Within collision threshold
            ContactPair pair;
            pair.type = ContactType::WALL;
            pair.idx0 = i;
            pair.gap = signed_dist;
            pair.normal = plane_normal;
            pair.witness_p = state.positions[i];
            pair.witness_q = state.positions[i] - signed_dist * plane_normal;
            pair.vertex_count = 1;
            pair.weights[0] = static_cast<Real>(1.0);
            contacts.push_back(pair);
        }
    }
}

// Full collision detection
void Collision::detect_all_collisions(const Mesh& mesh, const State& state,
                                     std::vector<ContactPair>& contacts) {
    contacts.clear();
    
    // Build BVHs
    std::vector<BVHNode> tri_bvh, edge_bvh;
    std::vector<int> tri_indices, edge_indices;
    
    build_triangle_bvh(mesh, state, tri_bvh, tri_indices);
    build_edge_bvh(mesh, state, edge_bvh, edge_indices);
    
    // Broad phase
    std::vector<ContactPair> candidates;
    broad_phase_triangles(mesh, state, tri_bvh, candidates);
    broad_phase_edges(mesh, state, tri_bvh, edge_bvh, candidates);
    
    // Narrow phase
    for (auto& pair : candidates) {
        if (pair.type == ContactType::POINT_TRIANGLE) {
            const Vec3& p = state.positions[pair.idx0];
            const Vec3& a = state.positions[pair.idx1];
            const Vec3& b = state.positions[pair.idx2];
            const Vec3& c = state.positions[pair.idx3];

            if (narrow_phase_point_triangle(p, a, b, c, pair.gap, pair.normal,
                                           pair.witness_p, pair.witness_q)) {
                if (pair.gap < 0.01) {  // Within collision threshold
                    Vec3 bary = compute_triangle_barycentric(pair.witness_q, a, b, c);
                    pair.barycentric = bary;
                    pair.weights[0] = static_cast<Real>(1.0);
                    pair.weights[1] = -bary[0];
                    pair.weights[2] = -bary[1];
                    pair.weights[3] = -bary[2];
                    pair.vertex_count = 4;
                    contacts.push_back(pair);
                }
            }
        } else if (pair.type == ContactType::EDGE_EDGE) {
            const Vec3& p0 = state.positions[pair.idx0];
            const Vec3& p1 = state.positions[pair.idx1];
            const Vec3& q0 = state.positions[pair.idx2];
            const Vec3& q1 = state.positions[pair.idx3];

            if (narrow_phase_edge_edge(p0, p1, q0, q1, pair.gap, pair.normal,
                                      pair.witness_p, pair.witness_q)) {
                if (pair.gap < 0.01) {  // Within collision threshold
                    pair.vertex_count = 4;
                    pair.weights[0] = static_cast<Real>(0.5);
                    pair.weights[1] = static_cast<Real>(0.5);
                    pair.weights[2] = static_cast<Real>(-0.5);
                    pair.weights[3] = static_cast<Real>(-0.5);
                    contacts.push_back(pair);
                }
            }
        }
    }
}

void Collision::detect_all_collisions(const Mesh& mesh, const State& state,
                                      const std::vector<RigidBody>& rigids,
                                      std::vector<ContactPair>& contacts) {
    contacts.clear();

    // Deformable self collisions
    detect_all_collisions(mesh, state, contacts);

    if (rigids.empty()) {
        return;
    }

    // Deformable vs rigid
    for (size_t rb = 0; rb < rigids.size(); ++rb) {
        const RigidBody& body = rigids[rb];
        std::vector<Vec3> rigid_vertices = body.world_vertices();

        for (size_t v = 0; v < state.positions.size(); ++v) {
            const Vec3& p = state.positions[v];

            for (const Triangle& tri : body.triangles()) {
                const Vec3& a = rigid_vertices[tri.v[0]];
                const Vec3& b = rigid_vertices[tri.v[1]];
                const Vec3& c = rigid_vertices[tri.v[2]];

                ContactPair pair;
                pair.type = ContactType::RIGID_POINT_TRIANGLE;
                pair.idx0 = static_cast<Index>(v);
                pair.idx1 = tri.v[0];
                pair.idx2 = tri.v[1];
                pair.idx3 = tri.v[2];
                pair.rigid_body_index = static_cast<int>(rb);

                if (narrow_phase_point_triangle(p, a, b, c, pair.gap, pair.normal,
                                                pair.witness_p, pair.witness_q)) {
                    if (pair.gap < 0.01) {
                        pair.vertex_count = 1;
                        pair.weights[0] = static_cast<Real>(1.0);
                        contacts.push_back(pair);
                    }
                }
            }
        }
    }
}

} // namespace ando_barrier
