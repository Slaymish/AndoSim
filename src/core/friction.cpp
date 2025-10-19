#include "friction.h"
#include <cmath>

namespace ando_barrier {

Real FrictionModel::compute_friction_stiffness(
    Real normal_force,
    Real friction_mu,
    Real friction_epsilon
) {
    // k_f = μ * |F_n| / ε²
    // Regularization prevents division by zero and limits stiffness growth
    Real epsilon_sq = friction_epsilon * friction_epsilon;
    Real stiffness = friction_mu * std::abs(normal_force) / epsilon_sq;
    
    // Cap maximum stiffness to prevent numerical issues
    // Max stiffness ~10^8 for typical parameters
    const Real max_stiffness = static_cast<Real>(1e8);
    return std::min(stiffness, max_stiffness);
}

Real FrictionModel::compute_energy(
    const Vec3& x_current,
    const Vec3& x_previous,
    const Vec3& contact_normal,
    Real friction_stiffness
) {
    // Compute displacement
    Vec3 displacement = x_current - x_previous;
    
    // Extract tangential component
    Vec3 tangential = extract_tangential(displacement, contact_normal);
    
    // Friction energy: V_f = (k_f / 2) * ||Δx_t||²
    Real tangential_mag_sq = tangential.squaredNorm();
    return static_cast<Real>(0.5) * friction_stiffness * tangential_mag_sq;
}

Vec3 FrictionModel::compute_gradient(
    const Vec3& x_current,
    const Vec3& x_previous,
    const Vec3& contact_normal,
    Real friction_stiffness
) {
    // Compute displacement
    Vec3 displacement = x_current - x_previous;
    
    // Extract tangential component
    Vec3 tangential = extract_tangential(displacement, contact_normal);
    
    // Gradient: ∇V_f = k_f * Δx_t
    // This is a restoring force opposing tangential motion
    return friction_stiffness * tangential;
}

Mat3 FrictionModel::compute_hessian(
    const Vec3& contact_normal,
    Real friction_stiffness
) {
    // Hessian: ∇²V_f = k_f * (I - n ⊗ n)
    // This projects onto tangent space (removes normal component)
    
    // Start with identity matrix scaled by stiffness
    Mat3 H = friction_stiffness * Mat3::Identity();
    
    // Subtract normal projection: n ⊗ n
    // This is equivalent to outer product: n * n^T
    H -= friction_stiffness * (contact_normal * contact_normal.transpose());
    
    // Result is symmetric and positive semi-definite (PSD)
    // Eigenvalues: {k_f, k_f, 0} where 0 corresponds to normal direction
    
    // For numerical stability, add small epsilon to ensure strict SPD
    const Real epsilon = static_cast<Real>(1e-8);
    H += epsilon * Mat3::Identity();
    
    return H;
}

Vec3 FrictionModel::extract_tangential(
    const Vec3& displacement,
    const Vec3& normal
) {
    // Tangential component: Δx_t = Δx - (Δx · n)n
    // This removes the normal component from displacement
    
    Real normal_component = displacement.dot(normal);
    Vec3 tangential = displacement - normal_component * normal;
    
    return tangential;
}

bool FrictionModel::should_apply_friction(
    const Vec3& tangential_displacement,
    Real threshold
) {
    // Only apply friction if tangential motion exceeds threshold
    // This prevents numerical noise from triggering friction on stationary contacts
    Real tangential_mag = tangential_displacement.norm();
    return tangential_mag > threshold;
}

} // namespace ando_barrier
