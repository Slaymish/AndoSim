#include "stiffness.h"
#include "elasticity.h"
#include <Eigen/Eigenvalues>
#include <algorithm>

namespace ando_barrier {

Real Stiffness::compute_contact_stiffness(
    Real mass,
    Real dt,
    Real gap,
    Real g_max,
    const Vec3& normal,
    const Mat3& H_block,
    Real min_gap
) {
    // Base inertial term: m/Δt²
    Real k_inertial = mass / (dt * dt);

    // Elasticity contribution: n·(H n)
    Mat3 H = H_block;
    enforce_spd(H);

    Vec3 n = normal;
    Real n_norm = n.norm();
    if (n_norm > Real(1e-9)) {
        n /= n_norm;
    } else {
        n = Vec3(0.0, 1.0, 0.0);
    }

    Vec3 Hn = H * n;
    Real k_elastic = std::max(Real(0.0), n.dot(Hn));

    // Takeover term with ĝ clamp (Section 3.3/3.4)
    Real g_clamped = std::max(std::max(gap, min_gap), Real(1e-12));
    Real g_hat = std::min(g_clamped, g_max);
    Real k_takeover = mass / (g_hat * g_hat);

    // Ensure takeover only active within barrier window
    if (gap >= g_max) {
        k_takeover = Real(0.0);
    }

    return k_inertial + k_elastic + k_takeover;
}

Real Stiffness::compute_pin_stiffness(
    Real mass,
    Real dt,
    const Vec3& offset,
    const Mat3& H_block,
    Real min_gap
) {
    // Base inertial term: m/Δt²
    Real k_inertial = mass / (dt * dt);

    // Elasticity contribution along pin direction
    Mat3 H = H_block;
    enforce_spd(H);

    Vec3 dir = offset;
    Real length = dir.norm();
    if (length > Real(1e-9)) {
        dir /= length;
    } else {
        dir = Vec3(1.0, 0.0, 0.0);
    }

    Real k_elastic = std::max(Real(0.0), dir.dot(H * dir));

    Real g_hat = std::max(std::max(length, min_gap), Real(1e-12));
    Real k_takeover = mass / (g_hat * g_hat);

    return k_inertial + k_elastic + k_takeover;
}

Real Stiffness::compute_wall_stiffness(
    Real mass,
    Real wall_gap,
    const Vec3& normal,
    const Mat3& H_block,
    Real min_gap
) {
    // Wall stiffness: k = m/(g_wall)² + n·(H n)
    Real g_hat = std::max(std::max(wall_gap, min_gap), Real(1e-12));
    Real k_inertial = mass / (g_hat * g_hat);

    Mat3 H = H_block;
    enforce_spd(H);

    Vec3 n = normal;
    Real n_norm = n.norm();
    if (n_norm > Real(1e-9)) {
        n /= n_norm;
    } else {
        n = Vec3(0.0, 1.0, 0.0);
    }

    Vec3 Hn = H * n;
    Real k_elastic = std::max(Real(0.0), n.dot(Hn));

    return k_inertial + k_elastic;
}

void Stiffness::compute_all_stiffnesses(
    const Mesh& mesh,
    const State& state,
    const Constraints& constraints,
    Real dt,
    const SparseMatrix& H_elastic
) {
    // Individual stiffness functions should be called directly during gradient/Hessian assembly.
    // This function is reserved for future batch optimization if needed.
}

Mat3 Stiffness::extract_hessian_block(const SparseMatrix& H, Index vertex_idx) {
    Mat3 block = Mat3::Zero();
    
    // Extract 3×3 block from global sparse Hessian
    // Block starts at row/col = vertex_idx * 3
    Index base_idx = vertex_idx * 3;
    
    for (int k = 0; k < H.outerSize(); ++k) {
        for (SparseMatrix::InnerIterator it(H, k); it; ++it) {
            Index row = it.row();
            Index col = it.col();
            
            // Check if this entry belongs to our 3×3 block
            if (row >= base_idx && row < base_idx + 3 &&
                col >= base_idx && col < base_idx + 3) {
                block(row - base_idx, col - base_idx) = it.value();
            }
        }
    }
    
    return block;
}

void Stiffness::enforce_spd(Mat3& H, Real epsilon) {
    // Symmetrize
    H = (H + H.transpose()) * 0.5;
    
    // Eigenvalue clamping for SPD
    Eigen::SelfAdjointEigenSolver<Mat3> eigen_solver(H);
    Vec3 eigenvalues = eigen_solver.eigenvalues();
    Mat3 eigenvectors = eigen_solver.eigenvectors();
    
    // Clamp negative/small eigenvalues
    for (int i = 0; i < 3; ++i) {
        if (eigenvalues[i] < epsilon) {
            eigenvalues[i] = epsilon;
        }
    }
    
    // Reconstruct SPD matrix
    H = eigenvectors * eigenvalues.asDiagonal() * eigenvectors.transpose();
}

} // namespace ando_barrier

