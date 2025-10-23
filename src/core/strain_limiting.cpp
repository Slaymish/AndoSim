#include "strain_limiting.h"
#include "barrier.h"

#include <algorithm>
#include <array>
#include <cmath>

namespace ando_barrier {

namespace {

constexpr Real kTinyValue = static_cast<Real>(1e-12);

} // namespace

StrainLimiting::Mat32 StrainLimiting::compute_deformation_gradient(
    const Vec3& v0,
    const Vec3& v1,
    const Vec3& v2,
    const Mat2& Dm_inv
) {
    Mat32 Ds;
    Ds.col(0) = v1 - v0;
    Ds.col(1) = v2 - v0;
    return Ds * Dm_inv;
}

bool StrainLimiting::compute_svd(
    const Mat32& F,
    Eigen::Matrix<Real, 3, 2>& U,
    Vec2& singular_values,
    Mat2& V
) {
    Eigen::JacobiSVD<Mat32> svd(
        F,
        Eigen::ComputeFullU | Eigen::ComputeFullV
    );

    singular_values = svd.singularValues();
    U = svd.matrixU().leftCols<2>();
    V = svd.matrixV();

    if (singular_values[0] < kDegenerateThreshold ||
        singular_values[1] < kDegenerateThreshold) {
        singular_values[0] = std::max(singular_values[0], kDegenerateThreshold);
        singular_values[1] = std::max(singular_values[1], kDegenerateThreshold);
    }

    return std::isfinite(singular_values[0]) && std::isfinite(singular_values[1]);
}

StrainLimiting::Mat99 StrainLimiting::extract_face_hessian_block(
    const SparseMatrix& H,
    const Triangle& tri
) {
    Mat99 block = Mat99::Zero();
    std::array<Index, 3> verts = {tri.v[0], tri.v[1], tri.v[2]};

    std::array<Index, 3> row_lookup = verts;

    for (int outer = 0; outer < H.outerSize(); ++outer) {
        for (SparseMatrix::InnerIterator it(H, outer); it; ++it) {
            Index global_row = it.row() / 3;
            Index global_col = it.col() / 3;

            int local_row = -1;
            int local_col = -1;
            for (int i = 0; i < 3; ++i) {
                if (row_lookup[i] == global_row) {
                    local_row = i;
                }
                if (row_lookup[i] == global_col) {
                    local_col = i;
                }
            }

            if (local_row < 0 || local_col < 0) {
                continue;
            }

            int row_component = static_cast<int>(it.row() % 3);
            int col_component = static_cast<int>(it.col() % 3);

            int r = local_row * 3 + row_component;
            int c = local_col * 3 + col_component;
            block(r, c) += it.value();
        }
    }

    return block;
}

StrainLimiting::Vec9 StrainLimiting::build_relative_direction(
    const Vec3& x0,
    const Vec3& x1,
    const Vec3& x2
) {
    Vec3 centroid = (x0 + x1 + x2) / static_cast<Real>(3.0);
    Vec9 w;
    w.segment<3>(0) = x0 - centroid;
    w.segment<3>(3) = x1 - centroid;
    w.segment<3>(6) = x2 - centroid;
    return w;
}

Real StrainLimiting::to_fraction(Real value) {
    if (value > Real(1.0)) {
        return value * Real(0.01);
    }
    return value;
}

void StrainLimiting::rebuild_constraints(
    const Mesh& mesh,
    const State& state,
    const SimParams& params,
    const SparseMatrix& H_elastic,
    Constraints& constraints
) {
    constraints.clear_strain_limits();

    if (!params.enable_strain_limiting) {
        return;
    }

    Real tau = to_fraction(params.strain_tau);
    Real epsilon = params.strain_epsilon > Real(0.0)
        ? to_fraction(params.strain_epsilon)
        : tau;
    if (epsilon <= Real(0.0)) {
        return; // Nothing to enforce
    }

    const Real min_gap = std::max(params.min_gap, Real(1e-8));

    for (size_t face = 0; face < mesh.num_triangles(); ++face) {
        const Triangle& tri = mesh.triangles[face];
        const Mat2& Dm_inv = mesh.Dm_inv[face];

        if (mesh.rest_areas[face] <= kTinyValue) {
            continue; // Degenerate rest face
        }

        Mat32 F = compute_deformation_gradient(
            state.positions[tri.v[0]],
            state.positions[tri.v[1]],
            state.positions[tri.v[2]],
            Dm_inv
        );

        Eigen::Matrix<Real, 3, 2> U;
        Vec2 sigma;
        Mat2 V;
        if (!compute_svd(F, U, sigma, V)) {
            continue;
        }

        Real face_mass = mesh.rest_areas[face] *
            mesh.material.thickness * mesh.material.density;

        Vec9 w_r = build_relative_direction(
            state.positions[tri.v[0]],
            state.positions[tri.v[1]],
            state.positions[tri.v[2]]
        );

        Mat99 H_block = extract_face_hessian_block(H_elastic, tri);
        Mat99 H_sym = (H_block + H_block.transpose()) * Real(0.5);
        Real elastic_term = w_r.dot(H_sym * w_r);
        elastic_term = std::max(elastic_term, Real(0.0));

        for (int s = 0; s < 2; ++s) {
            Real sigma_val = sigma[s];
            Real gap = (Real(1.0) + tau + epsilon) - sigma_val;
            if (!Barrier::in_domain(gap, epsilon)) {
                continue;
            }

            Real gap_clamped = std::max(std::abs(gap), min_gap);
            Real inertial_term = face_mass / (gap_clamped * gap_clamped);
            Real stiffness = inertial_term + elastic_term;

            StrainConstraint constraint;
            constraint.face_idx = static_cast<Index>(face);
            constraint.sigma = sigma_val;
            constraint.singular_index = s;
            constraint.stiffness = stiffness;
            constraint.active = true;

            constraints.strain_limits.push_back(constraint);
        }
    }
}

void StrainLimiting::accumulate_gradient(
    const Mesh& mesh,
    const State& state,
    const Constraints& constraints,
    const SimParams& params,
    VecX& gradient
) {
    if (!params.enable_strain_limiting || constraints.strain_limits.empty()) {
        return;
    }

    Real tau = to_fraction(params.strain_tau);
    Real epsilon = params.strain_epsilon > Real(0.0)
        ? to_fraction(params.strain_epsilon)
        : tau;
    const Real svd_epsilon = std::max(params.strain_svd_epsilon, Real(1e-8));

    for (const auto& constraint : constraints.strain_limits) {
        if (!constraint.active) {
            continue;
        }

        Index face_idx = constraint.face_idx;
        if (face_idx < 0 ||
            static_cast<size_t>(face_idx) >= mesh.num_triangles()) {
            continue;
        }

        const Triangle& tri = mesh.triangles[face_idx];
        const Mat2& Dm_inv = mesh.Dm_inv[face_idx];

        Mat32 F = compute_deformation_gradient(
            state.positions[tri.v[0]],
            state.positions[tri.v[1]],
            state.positions[tri.v[2]],
            Dm_inv
        );

        Eigen::Matrix<Real, 3, 2> U;
        Vec2 sigma;
        Mat2 V;
        if (!compute_svd(F, U, sigma, V)) {
            continue;
        }

        int idx = std::clamp(constraint.singular_index, 0, 1);

        Eigen::Matrix<Real, 3, 2> dSigma_dF;
        if (std::abs(sigma[0] - sigma[1]) < svd_epsilon) {
            dSigma_dF = (U.col(0) * V.col(0).transpose() +
                         U.col(1) * V.col(1).transpose()) * Real(0.5);
        } else {
            dSigma_dF = U.col(idx) * V.col(idx).transpose();
        }

        Real gap = (Real(1.0) + tau + epsilon) - sigma[idx];
        if (!Barrier::in_domain(gap, epsilon)) {
            continue;
        }

        Real dV_dg = Barrier::compute_gradient(gap, epsilon, constraint.stiffness);
        if (std::abs(dV_dg) < kTinyValue) {
            continue;
        }

        Mat32 dPsi_dF = -dV_dg * dSigma_dF;
        Mat32 mapped = dPsi_dF * Dm_inv.transpose();

        Vec3 grad1 = mapped.col(0);
        Vec3 grad2 = mapped.col(1);
        Vec3 grad0 = -(grad1 + grad2);

        gradient.segment<3>(tri.v[0] * 3) += grad0;
        gradient.segment<3>(tri.v[1] * 3) += grad1;
        gradient.segment<3>(tri.v[2] * 3) += grad2;
    }
}

void StrainLimiting::accumulate_hessian(
    const Mesh& mesh,
    const State& state,
    const Constraints& constraints,
    const SimParams& params,
    std::vector<Triplet>& triplets
) {
    if (!params.enable_strain_limiting || constraints.strain_limits.empty()) {
        return;
    }

    Real tau = to_fraction(params.strain_tau);
    Real epsilon = params.strain_epsilon > Real(0.0)
        ? to_fraction(params.strain_epsilon)
        : tau;
    const Real svd_epsilon = std::max(params.strain_svd_epsilon, Real(1e-8));

    for (const auto& constraint : constraints.strain_limits) {
        if (!constraint.active) {
            continue;
        }

        Index face_idx = constraint.face_idx;
        if (face_idx < 0 ||
            static_cast<size_t>(face_idx) >= mesh.num_triangles()) {
            continue;
        }

        const Triangle& tri = mesh.triangles[face_idx];
        const Mat2& Dm_inv = mesh.Dm_inv[face_idx];

        Mat32 F = compute_deformation_gradient(
            state.positions[tri.v[0]],
            state.positions[tri.v[1]],
            state.positions[tri.v[2]],
            Dm_inv
        );

        Eigen::Matrix<Real, 3, 2> U;
        Vec2 sigma;
        Mat2 V;
        if (!compute_svd(F, U, sigma, V)) {
            continue;
        }

        int idx = std::clamp(constraint.singular_index, 0, 1);

        Eigen::Matrix<Real, 3, 2> dSigma_dF;
        if (std::abs(sigma[0] - sigma[1]) < svd_epsilon) {
            dSigma_dF = (U.col(0) * V.col(0).transpose() +
                         U.col(1) * V.col(1).transpose()) * Real(0.5);
        } else {
            dSigma_dF = U.col(idx) * V.col(idx).transpose();
        }

        Mat32 dSigma_dX = dSigma_dF * Dm_inv.transpose();

        Vec3 dSigma_dx1 = dSigma_dX.col(0);
        Vec3 dSigma_dx2 = dSigma_dX.col(1);
        Vec3 dSigma_dx0 = -(dSigma_dx1 + dSigma_dx2);

        Eigen::Matrix<Real, 9, 1> J;
        J.segment<3>(0) = dSigma_dx0;
        J.segment<3>(3) = dSigma_dx1;
        J.segment<3>(6) = dSigma_dx2;

        Real gap = (Real(1.0) + tau + epsilon) - sigma[idx];
        if (!Barrier::in_domain(gap, epsilon)) {
            continue;
        }

        Real d2V = Barrier::compute_hessian(gap, epsilon, constraint.stiffness);
        if (std::abs(d2V) < kTinyValue) {
            continue;
        }

        Eigen::Matrix<Real, 9, 9> H_local = d2V * (J * J.transpose());

        Index vertices[3] = {tri.v[0], tri.v[1], tri.v[2]};

        for (int a = 0; a < 3; ++a) {
            for (int b = 0; b < 3; ++b) {
                Mat3 block = H_local.block<3, 3>(a * 3, b * 3);
                if (block.cwiseAbs().maxCoeff() < kTinyValue) {
                    continue;
                }

                Index ia = vertices[a];
                Index ib = vertices[b];

                for (int i = 0; i < 3; ++i) {
                    for (int j = 0; j < 3; ++j) {
                        Real value = block(i, j);
                        if (std::abs(value) < kTinyValue) {
                            continue;
                        }
                        triplets.emplace_back(ia * 3 + i, ib * 3 + j, value);
                    }
                }
            }
        }
    }
}

} // namespace ando_barrier
