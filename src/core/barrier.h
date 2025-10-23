#pragma once

#include "types.h"
#include "constraints.h"
#include "collision.h"

namespace ando_barrier {

// Weak cubic barrier energy (Eq. 3 in paper)
// V_weak(g, ḡ, k̄) = (k̄ / (2ḡ)) (ḡ - g)³ for g ≤ ḡ, else 0
class Barrier {
public:
    // Scalar barrier functions (gap-space derivatives)
    static Real compute_energy(Real g, Real g_max, Real k);
    static Real compute_gradient(Real g, Real g_max, Real k);
    static Real compute_hessian(Real g, Real g_max, Real k);
    static bool in_domain(Real g, Real g_max);

    // Position-space derivatives for contacts (chain rule through gap function)
    // Point-triangle contact: ∂V/∂x = (∂V/∂g)(∂g/∂x)
    static void compute_contact_gradient(
        const ContactPair& contact,
        Real g_max,
        Real k_bar,  // Pre-computed stiffness (treated as constant)
        Real normal_epsilon,
        VecX& gradient  // Add to gradient (4 vertices × 3D)
    );

    static void compute_rigid_contact_gradient(
        const ContactPair& contact,
        Real g_max,
        Real k_bar,
        Real normal_epsilon,
        VecX& gradient
    );

    // Contact Hessian: ∂²V/∂x² = (∂²V/∂g²)(∂g/∂x)(∂g/∂x)ᵀ + (∂V/∂g)(∂²g/∂x²)
    static void compute_contact_hessian(
        const ContactPair& contact,
        Real g_max,
        Real k_bar,
        Real normal_epsilon,
        Real tolerance,
        std::vector<Triplet>& triplets  // Append 12×12 block contributions
    );

    static void compute_rigid_contact_hessian(
        const ContactPair& contact,
        Real g_max,
        Real k_bar,
        Real normal_epsilon,
        Real tolerance,
        std::vector<Triplet>& triplets
    );

    // Pin constraint derivatives: gap = ||x_i - p_target||
    static void compute_pin_gradient(
        Index vertex_idx,
        const Vec3& pin_target,
        const State& state,
        Real g_max,
        Real k_bar,
        Real normal_epsilon,
        VecX& gradient  // Add to vertex gradient
    );

    static void compute_pin_hessian(
        Index vertex_idx,
        const Vec3& pin_target,
        const State& state,
        Real g_max,
        Real k_bar,
        Real normal_epsilon,
        Real tolerance,
        std::vector<Triplet>& triplets  // Append 3×3 block
    );

    // Wall constraint derivatives: gap = n·x - offset
    static void compute_wall_gradient(
        Index vertex_idx,
        const Vec3& wall_normal,
        Real wall_offset,
        const State& state,
        Real g_max,
        Real k_bar,
        Real normal_epsilon,
        VecX& gradient
    );

    static void compute_wall_hessian(
        Index vertex_idx,
        const Vec3& wall_normal,
        Real wall_offset,
        const State& state,
        Real g_max,
        Real k_bar,
        Real normal_epsilon,
        Real tolerance,
        std::vector<Triplet>& triplets
    );
};

} // namespace ando_barrier
