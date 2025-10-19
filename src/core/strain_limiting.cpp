#include "strain_limiting.h"
#include "barrier.h"
#include <cmath>
#include <algorithm>

namespace ando_barrier {

namespace {

constexpr Real kDegenerateThreshold = static_cast<Real>(1e-8);

bool compute_deformed_shape_matrix(
    const Vec3& v0,
    const Vec3& v1,
    const Vec3& v2,
    Mat2& Ds,
    Vec3* t1_out,
    Vec3* t2_out,
    Vec3* normal_out
) {
    Vec3 e1 = v1 - v0;
    Vec3 e2 = v2 - v0;

    Real e1_norm = e1.norm();
    bool frame_ok = e1_norm > kDegenerateThreshold;

    Vec3 t1 = Vec3::UnitX();
    Vec3 t2 = Vec3::UnitY();
    Vec3 normal = Vec3::UnitZ();

    if (frame_ok) {
        t1 = e1 / e1_norm;

        Vec3 n = e1.cross(e2);
        Real n_norm = n.norm();
        if (n_norm <= kDegenerateThreshold) {
            // Nearly colinear; choose a stable orthogonal axis to build a plane
            Vec3 fallback = (std::abs(t1.x()) > std::abs(t1.z()))
                ? Vec3(-t1.y(), t1.x(), 0.0)
                : Vec3(0.0, -t1.z(), t1.y());
            Real fallback_norm = fallback.norm();
            if (fallback_norm <= kDegenerateThreshold) {
                // Fallback axis was also degenerate; pick canonical axis
                fallback = (std::abs(t1.dot(Vec3::UnitZ())) < 0.9)
                    ? Vec3::UnitZ()
                    : Vec3::UnitY();
                fallback_norm = fallback.norm();
            }
            fallback /= fallback_norm;
            n = t1.cross(fallback);
            n_norm = n.norm();
            frame_ok = n_norm > kDegenerateThreshold;
            if (frame_ok) {
                normal = n / n_norm;
                t2 = normal.cross(t1);
            }
        } else {
            normal = n / n_norm;
            t2 = normal.cross(t1);
        }
    }

    if (!frame_ok) {
        // Fallback to global axes (original behavior) to avoid NaNs
        Vec2 e1_xy = e1.head<2>();
        Vec2 e2_xy = e2.head<2>();
        Ds(0, 0) = e1_xy[0];
        Ds(1, 0) = e1_xy[1];
        Ds(0, 1) = e2_xy[0];
        Ds(1, 1) = e2_xy[1];

        if (t1_out) *t1_out = t1;
        if (t2_out) *t2_out = t2;
        if (normal_out) *normal_out = normal;
        return false;
    }

    Ds(0, 0) = e1.dot(t1);
    Ds(1, 0) = e1.dot(t2);
    Ds(0, 1) = e2.dot(t1);
    Ds(1, 1) = e2.dot(t2);

    if (t1_out) *t1_out = t1;
    if (t2_out) *t2_out = t2;
    if (normal_out) *normal_out = normal;
    return true;
}

} // anonymous namespace

Real StrainLimiting::compute_energy(
    const Mesh& mesh,
    const State& state,
    Real strain_limit,
    Real strain_tau
) {
    Real total_energy = 0.0;
    
    for (size_t i = 0; i < mesh.num_triangles(); ++i) {
        const Triangle& tri = mesh.triangles[i];
        const Mat2& Dm_inv = mesh.Dm_inv[i];
        
        // Compute deformation gradient using a rotation-invariant frame
        Mat2 Ds;
        compute_deformed_shape_matrix(
            state.positions[tri.v[0]],
            state.positions[tri.v[1]],
            state.positions[tri.v[2]],
            Ds,
            nullptr,
            nullptr,
            nullptr
        );
        Mat2 F = Ds * Dm_inv;
        
        // Check if strain limiting is needed
        if (!needs_strain_limiting(F, strain_limit, strain_tau)) {
            continue;  // Skip if below threshold
        }
        
        // Compute max singular value
        Real sigma_max = compute_max_singular_value(F);
        
        // Gap function: g = σ_max - σ_limit
        Real gap = sigma_max - strain_limit;
        
        // Strain stiffness (simplified: use constant for energy computation)
        // In practice, this should be computed from elasticity Hessian
        Real k_strain = mesh.material.youngs_modulus * mesh.material.thickness * mesh.rest_areas[i];
        
        // Barrier energy: V_weak(g, τ, k)
        Real barrier_energy = Barrier::compute_energy(gap, strain_tau, k_strain);
        
        total_energy += barrier_energy;
    }
    
    return total_energy;
}

void StrainLimiting::compute_gradient(
    const Mesh& mesh,
    const State& state,
    Real strain_limit,
    Real strain_tau,
    VecX& gradient
) {
    for (size_t i = 0; i < mesh.num_triangles(); ++i) {
        const Triangle& tri = mesh.triangles[i];
        const Mat2& Dm_inv = mesh.Dm_inv[i];
        
        Vec3 t1, t2;
        Mat2 Ds;
        compute_deformed_shape_matrix(
            state.positions[tri.v[0]],
            state.positions[tri.v[1]],
            state.positions[tri.v[2]],
            Ds,
            &t1,
            &t2,
            nullptr
        );
        Mat2 F = Ds * Dm_inv;
        
        // Check if strain limiting is needed
        if (!needs_strain_limiting(F, strain_limit, strain_tau)) {
            continue;
        }
        
        // Compute SVD: F = U Σ V^T
        auto [U, sigma, V] = compute_svd(F);
        Real sigma_max = std::max(sigma[0], sigma[1]);
        
        // Gap and stiffness
        Real gap = sigma_max - strain_limit;
        Real k_strain = mesh.material.youngs_modulus * mesh.material.thickness * mesh.rest_areas[i];
        
        // Barrier gradient: ∂V/∂g
        Real dV_dg = Barrier::compute_gradient(gap, strain_tau, k_strain);
        
        // Chain rule: ∂V/∂x = (∂V/∂g) * (∂g/∂σ_max) * (∂σ_max/∂F) * (∂F/∂x)
        // ∂g/∂σ_max = 1
        // ∂σ_max/∂F = u_max ⊗ v_max (outer product of max singular vectors)
        
        int max_idx = (sigma[0] > sigma[1]) ? 0 : 1;
        Vec2 u_max = U.col(max_idx);
        Vec2 v_max = V.col(max_idx);
        
        // ∂σ_max/∂F = u_max ⊗ v_max
        Mat2 dSigma_dF = u_max * v_max.transpose();
        Mat2 P = dV_dg * dSigma_dF;
        
        // Map 2D forces back into 3D using the local frame
        Mat2 H = P * Dm_inv.transpose();
        Vec3 grad1 = H(0, 0) * t1 + H(1, 0) * t2;
        Vec3 grad2 = H(0, 1) * t1 + H(1, 1) * t2;
        Vec3 grad0 = -(grad1 + grad2);
        
        gradient.segment<3>(3 * tri.v[0]) += grad0;
        gradient.segment<3>(3 * tri.v[1]) += grad1;
        gradient.segment<3>(3 * tri.v[2]) += grad2;
    }
}

void StrainLimiting::compute_hessian(
    const Mesh& mesh,
    const State& state,
    Real strain_limit,
    Real strain_tau,
    std::vector<Triplet>& triplets
) {
    // Simplified Hessian: diagonal approximation for stability
    // Full Hessian derivation is complex (second derivatives of SVD)
    
    for (size_t i = 0; i < mesh.num_triangles(); ++i) {
        const Triangle& tri = mesh.triangles[i];
        const Mat2& Dm_inv = mesh.Dm_inv[i];
        
        Mat2 Ds;
        compute_deformed_shape_matrix(
            state.positions[tri.v[0]],
            state.positions[tri.v[1]],
            state.positions[tri.v[2]],
            Ds,
            nullptr,
            nullptr,
            nullptr
        );
        Mat2 F = Ds * Dm_inv;
        
        if (!needs_strain_limiting(F, strain_limit, strain_tau)) {
            continue;
        }
        
        Real sigma_max = compute_max_singular_value(F);
        Real gap = sigma_max - strain_limit;
        Real k_strain = mesh.material.youngs_modulus * mesh.material.thickness * mesh.rest_areas[i];
        
        // Barrier Hessian: ∂²V/∂g²
        Real d2V_dg2 = Barrier::compute_hessian(gap, strain_tau, k_strain);
        
        // Diagonal approximation: distribute stiffness to vertices
        Real stiffness_per_vertex = d2V_dg2 / 3.0;
        
        for (int j = 0; j < 3; ++j) {
            int idx = static_cast<int>(tri.v[j]);
            for (int k = 0; k < 3; ++k) {
                triplets.push_back(Triplet(3*idx + k, 3*idx + k, stiffness_per_vertex));
            }
        }
    }
}

Mat2 StrainLimiting::compute_deformation_gradient(
    const Vec3& v0,
    const Vec3& v1,
    const Vec3& v2,
    const Mat2& Dm_inv
) {
    Mat2 Ds;
    compute_deformed_shape_matrix(v0, v1, v2, Ds, nullptr, nullptr, nullptr);
    return Ds * Dm_inv;
}

std::tuple<Mat2, Vec2, Mat2> StrainLimiting::compute_svd(const Mat2& F) {
    // Use Eigen's JacobiSVD for 2×2 matrices
    Eigen::JacobiSVD<Mat2> svd(F, Eigen::ComputeFullU | Eigen::ComputeFullV);
    
    Mat2 U = svd.matrixU();
    Vec2 sigma = svd.singularValues();
    Mat2 V = svd.matrixV();
    
    // Clamp small singular values to avoid numerical issues
    const Real epsilon = static_cast<Real>(1e-8);
    sigma[0] = std::max(sigma[0], epsilon);
    sigma[1] = std::max(sigma[1], epsilon);
    
    return {U, sigma, V};
}

Real StrainLimiting::compute_max_singular_value(const Mat2& F) {
    // For 2×2 matrix, max singular value can be computed directly
    // σ_max = sqrt(λ_max(F^T F))
    Mat2 FtF = F.transpose() * F;
    
    // Eigenvalues of 2×2 symmetric matrix
    Real trace = FtF.trace();
    Real det = FtF.determinant();
    Real discriminant = trace * trace - 4.0 * det;
    discriminant = std::max(discriminant, static_cast<Real>(0.0));  // Avoid negative due to numerics
    
    Real lambda_max = (trace + std::sqrt(discriminant)) / 2.0;
    Real sigma_max = std::sqrt(std::max(lambda_max, static_cast<Real>(0.0)));
    
    return sigma_max;
}

bool StrainLimiting::needs_strain_limiting(
    const Mat2& F,
    Real strain_limit,
    Real strain_tau
) {
    Real sigma_max = compute_max_singular_value(F);
    Real gap = sigma_max - strain_limit;
    
    // Apply barrier if gap < τ (inside barrier domain)
    return gap < strain_tau;
}

Real StrainLimiting::compute_strain_stiffness(const Mat3& H_elastic_block) {
    // Simplified: use trace as measure of stiffness
    return H_elastic_block.trace() / 2.0;
}

} // namespace ando_barrier
