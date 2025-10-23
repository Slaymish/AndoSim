#pragma once

#include "types.h"
#include "mesh.h"
#include "state.h"
#include "constraints.h"
#include "collision.h"

namespace ando_barrier {

// Dynamic elasticity-inclusive stiffness computation
// Section 3.3-3.4 of the paper: k = m/Δt² + n·(H n)
class Stiffness {
public:
    // Contact stiffness (Eq. 5): k = m/Δt² + n·(H n)
    // With m/ĝ² takeover near tiny gaps
    static Real compute_contact_stiffness(
        const ContactPair& contact,
        const State& state,
        Real dt,
        const SparseMatrix& H_elastic
    );
    
    // Pin stiffness (Eq. 6): k_i = m_i/Δt² + w_i·(H_i w_i)
    // where w_i = x_i - P_fixed
    static Real compute_pin_stiffness(
        Real mass,              // Vertex mass
        Real dt,                // Time step
        const Vec3& offset,     // w_i = current_pos - pin_target
        const Mat3& H_block,    // Elasticity Hessian 3×3 block for this vertex
        Real min_gap            // Minimum separation used for takeover
    );
    
    // Wall stiffness (Eq. 7): k_wall = m_i/(g_wall)² + n_wall·(H_i n_wall)
    static Real compute_wall_stiffness(
        Real mass,              // Vertex mass
        Real wall_gap,          // Prescribed wall gap distance
        const Vec3& normal,     // Wall normal
        const Mat3& H_block,    // Elasticity Hessian 3×3 block for this vertex
        Real min_gap            // Minimum separation used for takeover
    );
    
    // Compute all contact stiffnesses for current constraints
    static void compute_all_stiffnesses(
        const Mesh& mesh,
        const State& state,
        Constraints& constraints,
        Real dt,
        const SparseMatrix& H_elastic  // Global elasticity Hessian
    );
    
    // Extract 3×3 Hessian block for a vertex from sparse global Hessian
    static Mat3 extract_hessian_block(const SparseMatrix& H, Index vertex_idx);
    
    // Ensure SPD and add regularization if needed
    static void enforce_spd(Mat3& H, Real epsilon = 1e-8);
};

} // namespace ando_barrier
