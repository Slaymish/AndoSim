#pragma once

#include "types.h"
#include "mesh.h"
#include "state.h"
#include <Eigen/Dense>
#include <Eigen/SVD>

namespace ando_barrier {

/**
 * Strain limiting with cubic barrier (Paper Section 3.2)
 * 
 * Prevents excessive stretching by applying barrier energy when
 * largest singular value exceeds strain limit.
 * 
 * Per-face strain barrier:
 * V_strain(F) = V_weak(σ_max - σ_limit, τ, k_SL)
 * where:
 * - F = deformation gradient (Ds * Dm_inv)
 * - σ_max = largest singular value (max stretch)
 * - σ_limit = user-specified limit (e.g., 1.05 = 5% stretch)
 * - τ = barrier range (default: 0.01)
 * - k_SL = strain stiffness (from elasticity Hessian)
 */
class StrainLimiting {
public:
    /**
     * Compute total strain limiting energy across all faces
     * 
     * @param mesh Mesh with rest-state data
     * @param state Current positions and velocities
     * @param strain_limit Maximum allowed stretch (1.0 = no stretch, 1.05 = 5%)
     * @param strain_tau Barrier range parameter
     * @return Total strain energy (scalar)
     */
    static Real compute_energy(
        const Mesh& mesh,
        const State& state,
        Real strain_limit,
        Real strain_tau
    );
    
    /**
     * Compute strain limiting gradient (forces)
     * 
     * Accumulates gradient contributions to provided vector.
     * 
     * @param mesh Mesh with rest-state data
     * @param state Current positions
     * @param strain_limit Maximum allowed stretch
     * @param strain_tau Barrier range
     * @param gradient Output vector (3N, accumulated)
     */
    static void compute_gradient(
        const Mesh& mesh,
        const State& state,
        Real strain_limit,
        Real strain_tau,
        VecX& gradient
    );
    
    /**
     * Compute strain limiting Hessian contributions
     * 
     * Adds triplets to provided vector for sparse assembly.
     * 
     * @param mesh Mesh with rest-state data
     * @param state Current positions
     * @param strain_limit Maximum allowed stretch
     * @param strain_tau Barrier range
     * @param triplets Output triplet list (accumulated)
     */
    static void compute_hessian(
        const Mesh& mesh,
        const State& state,
        Real strain_limit,
        Real strain_tau,
        std::vector<Triplet>& triplets
    );
    
    /**
     * Compute deformation gradient for a single triangle
     * 
     * F = Ds * Dm_inv
     * where Ds = [x1-x0, x2-x0] (deformed edge vectors)
     * 
     * @param v0, v1, v2 Current vertex positions
     * @param Dm_inv Inverse of rest-state edge matrix (2×2)
     * @return Deformation gradient F (2×2)
     */
    static Mat2 compute_deformation_gradient(
        const Vec3& v0,
        const Vec3& v1,
        const Vec3& v2,
        const Mat2& Dm_inv
    );
    
    /**
     * Compute SVD of 2×2 deformation gradient
     * 
     * F = U Σ V^T
     * Handles degeneracies with epsilon clamping.
     * 
     * @param F Deformation gradient (2×2)
     * @return Tuple of (U, singular_values, V)
     */
    static std::tuple<Mat2, Vec2, Mat2> compute_svd(const Mat2& F);
    
    /**
     * Extract largest singular value from deformation gradient
     * 
     * Faster than full SVD when only max stretch is needed.
     * 
     * @param F Deformation gradient (2×2)
     * @return σ_max (largest singular value)
     */
    static Real compute_max_singular_value(const Mat2& F);
    
    /**
     * Check if triangle needs strain limiting
     * 
     * Returns true if σ_max > σ_limit - τ (inside barrier domain).
     * 
     * @param F Deformation gradient
     * @param strain_limit Maximum allowed stretch
     * @param strain_tau Barrier range
     * @return True if barrier should be applied
     */
    static bool needs_strain_limiting(
        const Mat2& F,
        Real strain_limit,
        Real strain_tau
    );
    
    /**
     * Compute strain stiffness k_SL from elasticity Hessian
     * 
     * k_SL = trace(H_elastic) / 2
     * Simplified formula for per-face stiffness.
     * 
     * @param H_elastic Elasticity Hessian (9×9 block for triangle)
     * @return Strain stiffness scalar
     */
    static Real compute_strain_stiffness(const Mat3& H_elastic_block);
};

} // namespace ando_barrier
