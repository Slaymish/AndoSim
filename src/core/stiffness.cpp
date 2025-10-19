#include "stiffness.h"
#include "elasticity.h"
#include <Eigen/Eigenvalues>
#include <algorithm>

namespace ando_barrier {

Real Stiffness::compute_contact_stiffness(
    Real mass,
    Real dt,
    Real gap,
    const Vec3& normal,
    const Mat3& H_block,
    Real gap_threshold
) {
    // Base inertial term: m/Δt²
    Real k_inertial = mass / (dt * dt);
    
    // Elasticity contribution: n·(H n)
    // Ensure H is SPD first
    Mat3 H = H_block;
    enforce_spd(H);
    
    Vec3 Hn = H * normal;
    Real k_elastic = normal.dot(Hn);
    
    // Ensure non-negative (SPD enforcement should guarantee this)
    k_elastic = std::max(Real(0.0), k_elastic);
    
    // Takeover term for very small gaps: m/ĝ²
    // This prevents unbounded stiffness as gap → 0
    Real k_takeover = 0.0;
    if (gap < gap_threshold && gap > 0.0) {
        k_takeover = mass / (gap * gap);
    }
    
    // Total stiffness with takeover
    Real k_total = k_inertial + k_elastic + k_takeover;
    
    return k_total;
}

Real Stiffness::compute_pin_stiffness(
    Real mass,
    Real dt,
    const Vec3& offset,
    const Mat3& H_block
) {
    // Base inertial term: m/Δt²
    Real k_inertial = mass / (dt * dt);
    
    // Elasticity contribution: w·(H w)
    // where w = x - P_fixed (offset from pin target)
    Mat3 H = H_block;
    enforce_spd(H);
    
    // Normalize offset direction
    Vec3 w = offset;
    Real w_norm = w.norm();
    if (w_norm > 1e-10) {
        w /= w_norm;
    } else {
        // If at pin position, use identity direction
        w = Vec3(1.0, 0.0, 0.0);
    }
    
    Vec3 Hw = H * w;
    Real k_elastic = w.dot(Hw);
    k_elastic = std::max(Real(0.0), k_elastic);
    
    return k_inertial + k_elastic;
}

Real Stiffness::compute_wall_stiffness(
    Real mass,
    Real gap,
    const Vec3& normal,
    const Mat3& H_block
) {
    // Wall stiffness: k = m/(g_wall)² + n·(H n)
    Real k_inertial = mass / (gap * gap);
    
    Mat3 H = H_block;
    enforce_spd(H);
    
    Vec3 Hn = H * normal;
    Real k_elastic = normal.dot(Hn);
    k_elastic = std::max(Real(0.0), k_elastic);
    
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

