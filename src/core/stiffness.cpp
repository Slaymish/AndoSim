#include "stiffness.h"
#include "elasticity.h"
#include <Eigen/Eigenvalues>
#include <algorithm>
#include <cmath>
#include <unordered_map>
#include <array>

namespace ando_barrier {

namespace {

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
        return Real(0.0);
    }
    n /= n_norm;

    const std::array<Index, 4> indices = {contact.idx0, contact.idx1, contact.idx2, contact.idx3};
    const int vertex_count = std::max(contact.vertex_count, 1);

    std::vector<Index> valid_vertices;
    std::vector<Real> valid_weights;
    valid_vertices.reserve(vertex_count);
    valid_weights.reserve(vertex_count);

    for (int i = 0; i < vertex_count; ++i) {
        Index idx = indices[i];
        if (idx < 0 || static_cast<size_t>(idx) >= state.masses.size()) {
            continue;
        }
        Real weight = contact.weights[i];
        if (weight == Real(0.0)) {
            continue;
        }
        valid_vertices.push_back(idx);
        valid_weights.push_back(weight);
    }

    if (valid_vertices.empty()) {
        return Real(0.0);
    }

    Real inertial = Real(0.0);
    for (size_t i = 0; i < valid_vertices.size(); ++i) {
        Real mass = state.masses[valid_vertices[i]];
        inertial += mass * valid_weights[i] * valid_weights[i];
    }
    inertial /= (dt * dt);

    const int block_count = static_cast<int>(valid_vertices.size());
    Eigen::Matrix<Real, Eigen::Dynamic, 1> Wn(3 * block_count);
    for (int i = 0; i < block_count; ++i) {
        Wn.segment<3>(3 * i) = valid_weights[i] * n;
    }

    auto H_sub = extract_submatrix(H_elastic, valid_vertices);
    Eigen::Matrix<Real, Eigen::Dynamic, 1> H_times = H_sub * Wn;
    Real elastic = Wn.dot(H_times);
    if (elastic < Real(0.0)) {
        elastic = Real(0.0);
    }

    return inertial + elastic;
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

