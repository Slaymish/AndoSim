#pragma once

#include "types.h"
#include "constraints.h"
#include "collision.h"

namespace ando_barrier {

// Cubic barrier energy implementation (Eq. in paper)
// V_weak(g, ḡ, k) = -(k/2)(g-ḡ)² ln(g/ḡ) for g ≤ ḡ, else 0
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
        const State& state,
        Real g_max,
        Real k_bar,  // Pre-computed stiffness (treated as constant)
        VecX& gradient  // Add to gradient (4 vertices × 3D)
    );

    static void compute_rigid_contact_gradient(
        const ContactPair& contact,
        Real g_max,
        Real k_bar,
        VecX& gradient
    );
    
    // Contact Hessian: ∂²V/∂x² = (∂²V/∂g²)(∂g/∂x)(∂g/∂x)ᵀ + (∂V/∂g)(∂²g/∂x²)
    static void compute_contact_hessian(
        const ContactPair& contact,
        const State& state,
        Real g_max,
        Real k_bar,
        std::vector<Triplet>& triplets  // Append 12×12 block contributions
    );

    static void compute_rigid_contact_hessian(
        const ContactPair& contact,
        Real g_max,
        Real k_bar,
        std::vector<Triplet>& triplets
    );
    
    // Pin constraint derivatives: gap = ||x_i - p_target||
    static void compute_pin_gradient(
        Index vertex_idx,
        const Vec3& pin_target,
        const State& state,
        Real g_max,
        Real k_bar,
        VecX& gradient  // Add to vertex gradient
    );
    
    static void compute_pin_hessian(
        Index vertex_idx,
        const Vec3& pin_target,
        const State& state,
        Real g_max,
        Real k_bar,
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
        VecX& gradient
    );
    
    static void compute_wall_hessian(
        Index vertex_idx,
        const Vec3& wall_normal,
        Real wall_offset,
        const State& state,
        Real g_max,
        Real k_bar,
        std::vector<Triplet>& triplets
    );

private:
    // Helper: compute gap gradient ∂g/∂x for point-triangle
    static void compute_gap_gradient_point_triangle(
        const Vec3& p, const Vec3& a, const Vec3& b, const Vec3& c,
        const Vec3& normal, Real gap,
        Vec3 grad[4]  // [grad_p, grad_a, grad_b, grad_c]
    );
    
    // Helper: compute gap Hessian ∂²g/∂x² for point-triangle
    static void compute_gap_hessian_point_triangle(
        const Vec3& p, const Vec3& a, const Vec3& b, const Vec3& c,
        const Vec3& normal, Real gap,
        Mat3 hess[4][4]  // 4×4 block matrix of 3×3 blocks
    );
};

} // namespace ando_barrier
