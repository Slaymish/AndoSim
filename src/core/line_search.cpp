#include "line_search.h"
#include <algorithm>
#include <cmath>
#include <iostream>

namespace ando_barrier {

Real LineSearch::search(const Mesh& mesh,
                       const State& state,
                       const VecX& direction,
                       const std::vector<ContactPair>& contacts,
                       const std::vector<Pin>& pins,
                       const Vec3& wall_normal,
                       Real wall_offset,
                       Real extension,
                       Real min_alpha) {
    
    // Start with full extended step
    Real alpha = 1.0;
    const Real reduction_factor = 0.5;  // Geometric backtracking
    const int max_iterations = 20;
    
    // Compute extended direction: d_ext = extension * d
    VecX extended_direction = extension * direction;
    
    // Flatten current positions to VecX
    VecX x;
    state.flatten_positions(x);
    
    // Try progressively smaller step lengths
    for (int iter = 0; iter < max_iterations; ++iter) {
        // Proposed new positions: x_new = x + α * extension * d
        VecX x_new = x + alpha * extended_direction;
        
        // Check feasibility (constraint satisfaction only, no energy evaluation)
        if (is_feasible(state, x_new, contacts, pins, wall_normal, wall_offset)) {
            return alpha;  // Found feasible step
        }
        
        // Reduce step length geometrically
        alpha *= reduction_factor;
        
        // Give up if step becomes too small
        if (alpha < min_alpha) {
            return 0.0;  // No feasible step found
        }
    }
    
    return alpha;  // Return best attempt
}

bool LineSearch::is_feasible(const State& state,
                             const VecX& x_new,
                             const std::vector<ContactPair>& contacts,
                             const std::vector<Pin>& pins,
                             const Vec3& wall_normal,
                             Real wall_offset,
                             Real gap_min) {
    
    // Flatten old positions
    VecX x_old;
    state.flatten_positions(x_old);
    const int n = static_cast<int>(x_old.size() / 3);
    
    auto get_pos = [](const VecX& x, int i) -> Vec3 {
        return Vec3(x[3*i], x[3*i+1], x[3*i+2]);
    };
    
    // 1. Check contact constraints with CCD
    for (const auto& contact : contacts) {
        if (contact.type == ContactType::POINT_TRIANGLE) {
            // Vertex vs triangle
            Vec3 p0 = get_pos(x_old, contact.idx0);
            Vec3 p1 = get_pos(x_new, contact.idx0);
            
            Vec3 a0 = get_pos(x_old, contact.idx1);
            Vec3 a1 = get_pos(x_new, contact.idx1);
            
            Vec3 b0 = get_pos(x_old, contact.idx2);
            Vec3 b1 = get_pos(x_new, contact.idx2);
            
            Vec3 c0 = get_pos(x_old, contact.idx3);
            Vec3 c1 = get_pos(x_new, contact.idx3);
            
            // CCD check: if collision time < 1.0, step is infeasible
            Real toi = ccd_point_triangle(p0, p1, a0, a1, b0, b1, c0, c1);
            if (toi < 1.0) {
                return false;  // Collision detected
            }
            
            // Also check discrete gap at end state
            Real distance;
            Vec3 normal, witness_p, witness_q;
            if (Collision::narrow_phase_point_triangle(p1, a1, b1, c1, 
                                                       distance, normal, witness_p, witness_q)) {
                if (distance < gap_min) {
                    return false;  // Gap too small
                }
            }
        }
        else if (contact.type == ContactType::EDGE_EDGE) {
            // Edge vs edge
            Vec3 p0_0 = get_pos(x_old, contact.idx0);
            Vec3 p0_1 = get_pos(x_new, contact.idx0);
            
            Vec3 p1_0 = get_pos(x_old, contact.idx1);
            Vec3 p1_1 = get_pos(x_new, contact.idx1);
            
            Vec3 q0_0 = get_pos(x_old, contact.idx2);
            Vec3 q0_1 = get_pos(x_new, contact.idx2);
            
            Vec3 q1_0 = get_pos(x_old, contact.idx3);
            Vec3 q1_1 = get_pos(x_new, contact.idx3);
            
            // CCD check
            Real toi = ccd_edge_edge(p0_0, p0_1, p1_0, p1_1, 
                                    q0_0, q0_1, q1_0, q1_1);
            if (toi < 1.0) {
                return false;  // Collision detected
            }
            
            // Discrete gap check
            Real distance;
            Vec3 normal, witness_p, witness_q;
            if (Collision::narrow_phase_edge_edge(p0_1, p1_1, q0_1, q1_1,
                                                  distance, normal, witness_p, witness_q)) {
                if (distance < gap_min) {
                    return false;  // Gap too small
                }
            }
        }
    }
    
    // 2. Check pin constraints (ensure they stay within barrier domain)
    for (const auto& pin : pins) {
        Vec3 x_pin = get_pos(x_new, pin.vertex_idx);
        Real distance = (x_pin - pin.target_position).norm();
        
        // Pin gap should remain positive (within barrier domain)
        // For pins, the "gap" is effectively the distance to target
        // Barrier domain is g ≤ ḡ, so we just need g > 0
        if (distance < gap_min) {
            return false;  // Pin would violate barrier domain
        }
    }
    
    // 3. Check wall constraint (if active)
    // Wall constraint: n·x - offset ≥ gap_min
    if (wall_normal.squaredNorm() > 0.5) {  // Check if wall is active
        for (int i = 0; i < n; ++i) {
            Vec3 pos = get_pos(x_new, i);
            Real signed_distance = wall_normal.dot(pos) - wall_offset;
            
            if (signed_distance < gap_min) {
                return false;  // Wall penetration
            }
        }
    }
    
    return true;  // All constraints satisfied
}

Real LineSearch::ccd_point_triangle(const Vec3& p0, const Vec3& p1,
                                   const Vec3& a0, const Vec3& a1,
                                   const Vec3& b0, const Vec3& b1,
                                   const Vec3& c0, const Vec3& c1) {
    // Conservative CCD using temporal sampling
    // Check if point trajectory crosses the triangle plane
    
    Vec3 dp = p1 - p0;
    Vec3 da = a1 - a0;
    Vec3 db = b1 - b0;
    Vec3 dc = c1 - c0;
    
    // Early exit if no motion
    if (dp.squaredNorm() < 1e-12 && da.squaredNorm() < 1e-12 &&
        db.squaredNorm() < 1e-12 && dc.squaredNorm() < 1e-12) {
        return 1.0;
    }
    
    // Sample at multiple time points for conservative detection
    const int num_samples = 10;
    for (int i = 1; i <= num_samples; ++i) {
        Real t = static_cast<Real>(i) / num_samples;
        
        // Interpolate positions
        Vec3 p_t = p0 + t * (p1 - p0);
        Vec3 a_t = a0 + t * (a1 - a0);
        Vec3 b_t = b0 + t * (b1 - b0);
        Vec3 c_t = c0 + t * (c1 - c0);
        
        // Check distance
        Real distance;
        Vec3 normal, witness_p, witness_q;
        if (Collision::narrow_phase_point_triangle(p_t, a_t, b_t, c_t,
                                                   distance, normal, witness_p, witness_q)) {
            if (distance < 1e-6) {  // Conservative threshold
                return t;  // Collision detected at time t
            }
        }
    }
    
    return 1.0;  // No collision detected
}

Real LineSearch::ccd_edge_edge(const Vec3& p0_0, const Vec3& p0_1,
                              const Vec3& p1_0, const Vec3& p1_1,
                              const Vec3& q0_0, const Vec3& q0_1,
                              const Vec3& q1_0, const Vec3& q1_1) {
    // Conservative CCD for edge-edge
    // Sample at multiple time points
    
    // Check if motion is negligible
    Vec3 dp0 = p0_1 - p0_0;
    Vec3 dp1 = p1_1 - p1_0;
    Vec3 dq0 = q0_1 - q0_0;
    Vec3 dq1 = q1_1 - q1_0;
    
    if (dp0.squaredNorm() < 1e-12 && dp1.squaredNorm() < 1e-12 &&
        dq0.squaredNorm() < 1e-12 && dq1.squaredNorm() < 1e-12) {
        return 1.0;  // No motion
    }
    
    // Sample at multiple time points
    const int num_samples = 10;
    for (int i = 1; i <= num_samples; ++i) {
        Real t = static_cast<Real>(i) / num_samples;
        
        // Interpolate edge positions
        Vec3 p0_t = p0_0 + t * (p0_1 - p0_0);
        Vec3 p1_t = p1_0 + t * (p1_1 - p1_0);
        Vec3 q0_t = q0_0 + t * (q0_1 - q0_0);
        Vec3 q1_t = q1_0 + t * (q1_1 - q1_0);
        
        // Check distance
        Real distance;
        Vec3 normal, witness_p, witness_q;
        if (Collision::narrow_phase_edge_edge(p0_t, p1_t, q0_t, q1_t,
                                              distance, normal, witness_p, witness_q)) {
            if (distance < 1e-6) {  // Conservative threshold
                return t;  // Collision detected at time t
            }
        }
    }
    
    return 1.0;  // No collision detected
}

} // namespace ando_barrier
