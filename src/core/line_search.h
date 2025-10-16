#pragma once

#include "types.h"
#include "mesh.h"
#include "state.h"
#include "collision.h"
#include "constraints.h"
#include <vector>

namespace ando_barrier {

/**
 * Constraint-only line search with extended direction (Section 3.5, Algorithm 1 Line 13)
 * 
 * Finds maximum α ∈ [0,1] such that x_new = x + α * extension * direction
 * satisfies all constraints (g ≥ 0 for contacts, pins within barrier domain).
 * 
 * Uses CCD (Continuous Collision Detection) to prevent pass-through.
 * No energy evaluation - constraint feasibility only for performance.
 */
class LineSearch {
public:
    /**
     * Search for feasible step length
     * 
     * @param mesh Mesh topology (for CCD checks)
     * @param state Current state (positions)
     * @param direction Search direction (typically Newton direction)
     * @param contacts Current contact constraints
     * @param pins Pin constraints (if any)
     * @param wall_normal Wall plane normal (if wall constraint active)
     * @param wall_offset Wall plane offset (if wall constraint active)
     * @param extension Extended direction multiplier (default 1.25 per paper)
     * @param min_alpha Minimum step length to consider (default 1e-6)
     * @return Maximum feasible α ∈ [0,1]
     */
    static Real search(const Mesh& mesh,
                      const State& state,
                      const VecX& direction,
                      const std::vector<ContactPair>& contacts,
                      const std::vector<Pin>& pins,
                      const Vec3& wall_normal = Vec3(0, 0, 1),
                      Real wall_offset = 0.0,
                      Real extension = 1.25,
                      Real min_alpha = 1e-6);

private:
    /**
     * Check if step is feasible for all constraints
     * 
     * @param state Current state
     * @param x_new Proposed new positions
     * @param contacts Contact constraints to check
     * @param pins Pin constraints to check
     * @param wall_normal Wall plane normal
     * @param wall_offset Wall plane offset
     * @param gap_min Minimum allowable gap (default 0)
     * @return true if all constraints satisfied
     */
    static bool is_feasible(const State& state,
                           const VecX& x_new,
                           const std::vector<ContactPair>& contacts,
                           const std::vector<Pin>& pins,
                           const Vec3& wall_normal,
                           Real wall_offset,
                           Real gap_min = 0.0);
    
    /**
     * Continuous Collision Detection for vertex-triangle pair
     * 
     * @param p0 Vertex position at t=0
     * @param p1 Vertex position at t=1
     * @param a0 Triangle vertex a at t=0
     * @param a1 Triangle vertex a at t=1
     * @param b0 Triangle vertex b at t=0
     * @param b1 Triangle vertex b at t=1
     * @param c0 Triangle vertex c at t=0
     * @param c1 Triangle vertex c at t=1
     * @return Time of impact (0 to 1) or 1.0 if no collision
     */
    static Real ccd_point_triangle(const Vec3& p0, const Vec3& p1,
                                  const Vec3& a0, const Vec3& a1,
                                  const Vec3& b0, const Vec3& b1,
                                  const Vec3& c0, const Vec3& c1);
    
    /**
     * Continuous Collision Detection for edge-edge pair
     * 
     * @param p0_0 Edge0 vertex 0 at t=0
     * @param p0_1 Edge0 vertex 0 at t=1
     * @param p1_0 Edge0 vertex 1 at t=0
     * @param p1_1 Edge0 vertex 1 at t=1
     * @param q0_0 Edge1 vertex 0 at t=0
     * @param q0_1 Edge1 vertex 0 at t=1
     * @param q1_0 Edge1 vertex 1 at t=0
     * @param q1_1 Edge1 vertex 1 at t=1
     * @return Time of impact (0 to 1) or 1.0 if no collision
     */
    static Real ccd_edge_edge(const Vec3& p0_0, const Vec3& p0_1,
                             const Vec3& p1_0, const Vec3& p1_1,
                             const Vec3& q0_0, const Vec3& q0_1,
                             const Vec3& q1_0, const Vec3& q1_1);
};

} // namespace ando_barrier
