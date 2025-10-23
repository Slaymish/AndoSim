#pragma once

#include "types.h"
#include "mesh.h"
#include "state.h"
#include "constraints.h"

#include <Eigen/Dense>
#include <Eigen/SVD>

namespace ando_barrier {

/**
 * Strain limiting with cubic barrier (Paper Section 3.2)
 *
 * Implements Eq. (8–9) from the paper using singular values of the
 * deformation gradient. Each overstretched face contributes a weak barrier
 * Ψ_SL(σ) = Ψ_weak(1 + τ + ε − σ, ε, k̄_SL) with dynamic stiffness
 * k̄_SL = m_face / gap² + w_rᵀ (H_r w_r).
 */
class StrainLimiting {
public:
    /**
     * Rebuild the set of active strain constraints for the current state.
     */
    static void rebuild_constraints(
        const Mesh& mesh,
        const State& state,
        const SimParams& params,
        const SparseMatrix& H_elastic,
        Constraints& constraints
    );

    /**
     * Accumulate gradient contributions from active strain constraints.
     */
    static void accumulate_gradient(
        const Mesh& mesh,
        const State& state,
        const Constraints& constraints,
        const SimParams& params,
        VecX& gradient
    );

    /**
     * Accumulate Hessian triplets from active strain constraints.
     */
    static void accumulate_hessian(
        const Mesh& mesh,
        const State& state,
        const Constraints& constraints,
        const SimParams& params,
        std::vector<Triplet>& triplets
    );

private:
    static constexpr Real kDegenerateThreshold = static_cast<Real>(1e-6);

    using Mat32 = Eigen::Matrix<Real, 3, 2>;
    using Vec9 = Eigen::Matrix<Real, 9, 1>;
    using Mat99 = Eigen::Matrix<Real, 9, 9>;

    static Mat32 compute_deformation_gradient(
        const Vec3& v0,
        const Vec3& v1,
        const Vec3& v2,
        const Mat2& Dm_inv
    );

    static bool compute_svd(
        const Mat32& F,
        Eigen::Matrix<Real, 3, 2>& U,
        Vec2& singular_values,
        Mat2& V
    );

    static Mat99 extract_face_hessian_block(
        const SparseMatrix& H,
        const Triangle& tri
    );

    static Vec9 build_relative_direction(
        const Vec3& x0,
        const Vec3& x1,
        const Vec3& x2
    );

    static Real to_fraction(Real value);
};

} // namespace ando_barrier

