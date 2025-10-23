#include "stiffness.h"
#include "elasticity.h"
#include <Eigen/Eigenvalues>
#include <algorithm>
#include <cmath>
#include <unordered_map>

namespace ando_barrier {

namespace {

static Vec3 compute_barycentric(const Vec3& p, const Vec3& a, const Vec3& b, const Vec3& c) {
    Vec3 v0 = b - a;
    Vec3 v1 = c - a;
    Vec3 v2 = p - a;

    Real d00 = v0.dot(v0);
    Real d01 = v0.dot(v1);
    Real d11 = v1.dot(v1);
    Real d20 = v2.dot(v0);
    Real d21 = v2.dot(v1);

    Real denom = d00 * d11 - d01 * d01;
    Real v = Real(0.0);
    Real w = Real(0.0);
    if (std::abs(denom) > Real(1e-12)) {
        v = (d11 * d20 - d01 * d21) / denom;
        w = (d00 * d21 - d01 * d20) / denom;
    }

    v = std::clamp(v, Real(0.0), Real(1.0));
    w = std::clamp(w, Real(0.0), Real(1.0));
    if (v + w > Real(1.0)) {
        Real sum = v + w;
        if (sum > Real(1e-12)) {
            v /= sum;
            w /= sum;
        }
    }

    Real u = Real(1.0) - v - w;
    return Vec3(u, v, w);
}

static Eigen::Matrix<Real, Eigen::Dynamic, Eigen::Dynamic> extract_submatrix(
    const SparseMatrix& H,
    const std::vector<Index>& vertices)
{
    const int block_count = static_cast<int>(vertices.size());
    Eigen::Matrix<Real, Eigen::Dynamic, Eigen::Dynamic> sub(3 * block_count, 3 * block_count);
    sub.setZero();

    std::unordered_map<Index, int> mapping;
    mapping.reserve(vertices.size());
    for (int i = 0; i < block_count; ++i) {
        mapping[vertices[i]] = i;
    }

    for (int k = 0; k < H.outerSize(); ++k) {
        for (SparseMatrix::InnerIterator it(H, k); it; ++it) {
            Index global_row_vertex = it.row() / 3;
            Index global_col_vertex = it.col() / 3;

            auto row_it = mapping.find(global_row_vertex);
            if (row_it == mapping.end()) continue;
            auto col_it = mapping.find(global_col_vertex);
            if (col_it == mapping.end()) continue;

            int local_row_vertex = row_it->second;
            int local_col_vertex = col_it->second;
            int row_component = static_cast<int>(it.row() % 3);
            int col_component = static_cast<int>(it.col() % 3);

            int row_index = local_row_vertex * 3 + row_component;
            int col_index = local_col_vertex * 3 + col_component;
            sub(row_index, col_index) += it.value();
        }
    }

    return sub;
}

} // namespace

Real Stiffness::compute_contact_stiffness(
    const ContactPair& contact,
    const State& state,
    Real dt,
    const SparseMatrix& H_elastic
) {
    if (dt <= Real(0.0)) {
        return Real(0.0);
    }

    Vec3 n = contact.normal;
    Real n_norm = n.norm();
    if (n_norm < Real(1e-12)) {
        n = Vec3(0.0, 1.0, 0.0);
        n_norm = Real(1.0);
    }

    std::vector<Index> vertices;
    std::vector<Real> weights;
    vertices.reserve(4);
    weights.reserve(4);

    if (contact.type == ContactType::POINT_TRIANGLE ||
        contact.type == ContactType::RIGID_POINT_TRIANGLE) {
        vertices.push_back(contact.idx0);
        weights.push_back(Real(1.0));

        if (contact.type == ContactType::POINT_TRIANGLE) {
            bool triangle_valid =
                contact.idx1 >= 0 && contact.idx2 >= 0 && contact.idx3 >= 0 &&
                static_cast<size_t>(contact.idx1) < state.positions.size() &&
                static_cast<size_t>(contact.idx2) < state.positions.size() &&
                static_cast<size_t>(contact.idx3) < state.positions.size();

            if (triangle_valid) {
                vertices.push_back(contact.idx1);
                vertices.push_back(contact.idx2);
                vertices.push_back(contact.idx3);

                const Vec3& a = state.positions[contact.idx1];
                const Vec3& b = state.positions[contact.idx2];
                const Vec3& c = state.positions[contact.idx3];
                Vec3 bary = compute_barycentric(contact.witness_q, a, b, c);

                Real u = bary[0];
                Real v = bary[1];
                Real w = bary[2];
                weights.push_back(-u);
                weights.push_back(-v);
                weights.push_back(-w);
            }
        }
    } else if (contact.type == ContactType::EDGE_EDGE) {
        vertices.push_back(contact.idx0);
        vertices.push_back(contact.idx1);
        vertices.push_back(contact.idx2);
        vertices.push_back(contact.idx3);

        weights = {Real(0.5), Real(0.5), Real(-0.5), Real(-0.5)};
    } else {
        vertices.push_back(contact.idx0);
        weights.push_back(Real(1.0));
    }

    // Filter invalid indices (e.g., rigid references)
    std::vector<Index> valid_vertices;
    std::vector<Real> valid_weights;
    valid_vertices.reserve(vertices.size());
    valid_weights.reserve(weights.size());
    for (size_t i = 0; i < vertices.size(); ++i) {
        Index idx = vertices[i];
        if (idx < 0 || static_cast<size_t>(idx) >= state.masses.size()) {
            continue;
        }
        valid_vertices.push_back(idx);
        valid_weights.push_back(weights[i]);
    }

    if (valid_vertices.empty()) {
        return Real(0.0);
    }

    // Average mass across participating vertices
    Real mass_sum = Real(0.0);
    for (Index idx : valid_vertices) {
        mass_sum += state.masses[idx];
    }
    Real mass_avg = mass_sum / static_cast<Real>(valid_vertices.size());

    // Inertial term
    Real k_inertial = mass_avg / (dt * dt);

    // Assemble W * n
    const int block_count = static_cast<int>(valid_vertices.size());
    Eigen::Matrix<Real, Eigen::Dynamic, 1> Wn(3 * block_count);
    Wn.setZero();
    for (int i = 0; i < block_count; ++i) {
        Wn.segment<3>(3 * i) = valid_weights[i] * n;
    }

    Real Wn_norm = Wn.norm();
    Real k_elastic = Real(0.0);

    if (Wn_norm > Real(1e-12)) {
        // Build W matrix
        Eigen::Matrix<Real, Eigen::Dynamic, Eigen::Dynamic> W(3 * block_count, 3);
        W.setZero();
        Mat3 I = Mat3::Identity();
        for (int i = 0; i < block_count; ++i) {
            W.block<3, 3>(3 * i, 0) = valid_weights[i] * I;
        }

        auto H_sub = extract_submatrix(H_elastic, valid_vertices);
        Eigen::Matrix<Real, 3, 3> H_eff =
            (W.transpose() * H_sub * W).template cast<Real>();
        H_eff = (H_eff + H_eff.transpose()) * Real(0.5);

        Mat3 H_spd = H_eff;
        enforce_spd(H_spd);

        Vec3 n_unit = n / n_norm;
        Vec3 Hn = H_spd * n_unit;
        Real directional = n_unit.dot(Hn);
        directional = std::max(Real(0.0), directional);
        k_elastic = Wn_norm * n_norm * directional;
    }

    return k_inertial + k_elastic;
}

Real Stiffness::compute_pin_stiffness(
    Real mass,
    Real dt,
    const Vec3& offset,
    const Mat3& H_block,
    Real min_gap
) {
    (void)dt;
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
    Real k_inertial = mass / (g_hat * g_hat);

    return k_inertial + k_elastic;
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
    Constraints& constraints,
    Real dt,
    const SparseMatrix& H_elastic
) {
    if (dt <= Real(0.0)) {
        return;
    }

    for (auto& contact : constraints.contacts) {
        if (!contact.active) {
            continue;
        }

        ContactPair pair;
        pair.normal = contact.normal;
        pair.gap = contact.gap;
        pair.witness_q = contact.witness_point;

        if (contact.triangle_idx >= 0 &&
            contact.triangle_idx < static_cast<Index>(mesh.triangles.size())) {
            const Triangle& tri = mesh.triangles[contact.triangle_idx];
            pair.type = ContactType::POINT_TRIANGLE;
            pair.idx0 = contact.vertex_idx;
            pair.idx1 = tri.v[0];
            pair.idx2 = tri.v[1];
            pair.idx3 = tri.v[2];
        } else {
            // Edge-edge constraints require explicit edge data which is not stored yet.
            // Skip until the constraint structure provides the participating vertices.
            continue;
        }

        contact.stiffness = compute_contact_stiffness(pair, state, dt, H_elastic);
    }
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

