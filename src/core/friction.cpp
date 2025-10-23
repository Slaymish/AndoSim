#include "friction.h"
#include <cmath>

namespace ando_barrier {

Real FrictionModel::compute_friction_stiffness(
    Real normal_force,
    Real friction_mu,
    Real friction_epsilon,
    Real tangential_displacement
) {
    Real denom = std::max(friction_epsilon, std::abs(tangential_displacement));
    if (denom <= static_cast<Real>(0.0)) {
        denom = friction_epsilon;
    }
    Real stiffness = friction_mu * std::abs(normal_force) / denom;
    
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
    Vec3 displacement = x_current - x_previous;
    Vec3 tangential = extract_tangential(displacement, contact_normal);
    
    // Gradient: ∇V_f = k_f * Δx_t (restoring force opposing tangential motion)
    return friction_stiffness * tangential;
}

Mat3 FrictionModel::compute_hessian(
    const Vec3& contact_normal,
    Real friction_stiffness
) {
    // Hessian: ∇²V_f = k_f * (I - n ⊗ n)
    // Projects onto tangent space (removes normal component)
    
    Mat3 H = friction_stiffness * Mat3::Identity();
    
    // Subtract normal projection: n ⊗ n
    H -= friction_stiffness * (contact_normal * contact_normal.transpose());
    
    // Result is PSD with eigenvalues: {k_f, k_f, 0} (0 in normal direction)
    // Add small epsilon for numerical stability
    const Real epsilon = static_cast<Real>(1e-8);
    H += epsilon * Mat3::Identity();
    
    return H;
}

Vec3 FrictionModel::extract_tangential(
    const Vec3& displacement,
    const Vec3& normal
) {
    // Tangential component: Δx_t = Δx - (Δx · n)n
    Real normal_component = displacement.dot(normal);
    Vec3 tangential = displacement - normal_component * normal;
    return tangential;
}

bool FrictionModel::should_apply_friction(
    const Vec3& tangential_displacement,
    Real threshold
) {
    // Apply friction only if tangential motion exceeds threshold
    // Prevents numerical noise from triggering friction on stationary contacts
    Real tangential_mag = tangential_displacement.norm();
    return tangential_mag > threshold;
}

} // namespace ando_barrier
