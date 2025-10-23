#pragma once

#include "types.h"
#include <Eigen/Dense>

namespace ando_barrier {

/**
 * Quadratic friction model from paper Section 3.7
 * 
 * Friction energy: V_f = (k_f / 2) * ||Δx_tangent||²
 * where Δx_tangent = relative tangential displacement
 * 
 * This is a regularized Coulomb friction model that remains differentiable
 * and suitable for Newton-based optimization.
 */
class FrictionModel {
public:
    /**
     * Compute friction stiffness from normal contact force
     * 
     * k_f = μ * |F_n| / ε²
     * where μ = friction coefficient, F_n = normal force, ε = regularization
     * 
     * @param normal_force Magnitude of normal contact force (N)
     * @param friction_mu Friction coefficient (0.0 = frictionless, 1.0 = very sticky)
     * @param friction_epsilon Regularization parameter (prevents singularity, ~0.001)
     * @return Friction stiffness k_f
     */
    static Real compute_friction_stiffness(
        Real normal_force,
        Real friction_mu,
        Real friction_epsilon,
        Real tangential_displacement
    );
    
    /**
     * Compute friction energy for a single contact
     * 
     * V_f = (k_f / 2) * ||Δx_t||²
     * where Δx_t = (Δx - (Δx · n)n) is tangential component
     * 
     * @param x_current Current vertex position
     * @param x_previous Previous vertex position (from last timestep)
     * @param contact_normal Contact normal vector (unit length)
     * @param friction_stiffness Pre-computed k_f
     * @return Friction energy scalar
     */
    static Real compute_energy(
        const Vec3& x_current,
        const Vec3& x_previous,
        const Vec3& contact_normal,
        Real friction_stiffness
    );
    
    /**
     * Compute friction gradient (force) w.r.t. current position
     * 
     * ∇V_f = k_f * Δx_t
     * where Δx_t is tangential displacement
     * 
     * @param x_current Current vertex position
     * @param x_previous Previous vertex position
     * @param contact_normal Contact normal vector (unit length)
     * @param friction_stiffness Pre-computed k_f
     * @return Gradient vector (3D force)
     */
    static Vec3 compute_gradient(
        const Vec3& x_current,
        const Vec3& x_previous,
        const Vec3& contact_normal,
        Real friction_stiffness
    );
    
    /**
     * Compute friction Hessian w.r.t. current position
     * 
     * ∇²V_f = k_f * (I - n ⊗ n)
     * where I is identity, n ⊗ n is outer product (projects out normal)
     * 
     * Result is a 3×3 symmetric matrix (tangent space projection scaled by k_f)
     * 
     * @param contact_normal Contact normal vector (unit length)
     * @param friction_stiffness Pre-computed k_f
     * @return Hessian matrix (3×3, symmetric, PSD)
     */
    static Mat3 compute_hessian(
        const Vec3& contact_normal,
        Real friction_stiffness
    );
    
    /**
     * Extract tangential component of displacement
     * 
     * Δx_t = Δx - (Δx · n)n
     * 
     * @param displacement Full displacement vector
     * @param normal Unit normal vector
     * @return Tangential displacement (perpendicular to normal)
     */
    static Vec3 extract_tangential(
        const Vec3& displacement,
        const Vec3& normal
    );
    
    /**
     * Check if friction should be applied (based on relative motion)
     * 
     * Only apply friction if there's tangential motion above threshold.
     * Prevents friction forces on stationary contacts (numerical noise).
     * 
     * @param tangential_displacement Tangential motion vector
     * @param threshold Minimum motion to trigger friction (default 1e-6)
     * @return True if friction should be applied
     */
    static bool should_apply_friction(
        const Vec3& tangential_displacement,
        Real threshold
    );
};

} // namespace ando_barrier
