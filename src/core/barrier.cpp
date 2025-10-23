#include "barrier.h"
#include "matrix_assembly.h"

#include <algorithm>
#include <cmath>
#include <limits>

namespace ando_barrier {

namespace {

inline bool has_valid_direction(const Vec3& n, Real eps) {
    return n.squaredNorm() > eps * eps;
}

inline Vec3 normalize_or_default(Vec3 n, Real eps) {
    if (has_valid_direction(n, eps)) {
        return n.normalized();
    }
    return Vec3(static_cast<Real>(0.0), static_cast<Real>(1.0), static_cast<Real>(0.0));
}

inline int contact_vertex_count(const ContactPair& contact) {
    return std::max(contact.vertex_count, 1);
}

} // namespace

Real Barrier::compute_energy(Real g, Real g_max, Real k) {
    if (g_max <= static_cast<Real>(0.0) || g >= g_max) {
        return static_cast<Real>(0.0);
    }

    Real delta = g_max - g;
    if (delta <= static_cast<Real>(0.0)) {
        return static_cast<Real>(0.0);
    }

    Real inv_gmax = static_cast<Real>(1.0) / g_max;
    return static_cast<Real>(0.5) * k * inv_gmax * delta * delta * delta;
}

Real Barrier::compute_gradient(Real g, Real g_max, Real k) {
    if (g_max <= static_cast<Real>(0.0) || g >= g_max) {
        return static_cast<Real>(0.0);
    }

    Real delta = g_max - g;
    Real inv_gmax = static_cast<Real>(1.0) / g_max;
    return -static_cast<Real>(1.5) * k * inv_gmax * delta * delta;
}

Real Barrier::compute_hessian(Real g, Real g_max, Real k) {
    if (g_max <= static_cast<Real>(0.0) || g >= g_max) {
        return static_cast<Real>(0.0);
    }

    Real delta = g_max - g;
    Real inv_gmax = static_cast<Real>(1.0) / g_max;
    return static_cast<Real>(3.0) * k * inv_gmax * delta;
}

bool Barrier::in_domain(Real g, Real g_max) {
    return g_max > static_cast<Real>(0.0) && g <= g_max;
}

void Barrier::compute_contact_gradient(
    const ContactPair& contact,
    Real g_max,
    Real k_bar,
    Real normal_epsilon,
    VecX& gradient) {

    if (!in_domain(contact.gap, g_max)) {
        return;
    }

    Vec3 normal = normalize_or_default(contact.normal, normal_epsilon);
    Real dV_dg = compute_gradient(contact.gap, g_max, k_bar);
    if (dV_dg == static_cast<Real>(0.0)) {
        return;
    }

    const std::array<Index, 4> indices = {contact.idx0, contact.idx1, contact.idx2, contact.idx3};
    const int count = contact_vertex_count(contact);

    for (int i = 0; i < count; ++i) {
        Index idx = indices[i];
        if (idx < 0) {
            continue;
        }
        Real weight = contact.weights[i];
        if (weight == static_cast<Real>(0.0)) {
            continue;
        }
        gradient.segment<3>(idx * 3) += dV_dg * weight * normal;
    }
}

void Barrier::compute_rigid_contact_gradient(
    const ContactPair& contact,
    Real g_max,
    Real k_bar,
    Real normal_epsilon,
    VecX& gradient) {
    compute_contact_gradient(contact, g_max, k_bar, normal_epsilon, gradient);
}

void Barrier::compute_contact_hessian(
    const ContactPair& contact,
    Real g_max,
    Real k_bar,
    Real normal_epsilon,
    Real tolerance,
    std::vector<Triplet>& triplets) {

    if (!in_domain(contact.gap, g_max)) {
        return;
    }

    Vec3 normal = normalize_or_default(contact.normal, normal_epsilon);
    Real d2V = compute_hessian(contact.gap, g_max, k_bar);
    if (d2V == static_cast<Real>(0.0)) {
        return;
    }

    const std::array<Index, 4> indices = {contact.idx0, contact.idx1, contact.idx2, contact.idx3};
    const int count = contact_vertex_count(contact);

    MatrixAssembly& cache = MatrixAssembly::instance();
    cache.ensure_contact_pattern(contact);

    for (int i = 0; i < count; ++i) {
        Real wi = contact.weights[i];
        if (wi == static_cast<Real>(0.0)) {
            continue;
        }
        Vec3 gi = wi * normal;
        for (int j = 0; j < count; ++j) {
            Real wj = contact.weights[j];
            if (wj == static_cast<Real>(0.0)) {
                continue;
            }
            Vec3 gj = wj * normal;
            Mat3 block = d2V * (gi * gj.transpose());
            cache.append_contact_block(contact, i, j, block, tolerance, triplets);
        }
    }
}

void Barrier::compute_rigid_contact_hessian(
    const ContactPair& contact,
    Real g_max,
    Real k_bar,
    Real normal_epsilon,
    Real tolerance,
    std::vector<Triplet>& triplets) {
    compute_contact_hessian(contact, g_max, k_bar, normal_epsilon, tolerance, triplets);
}

void Barrier::compute_pin_gradient(
    Index vertex_idx,
    const Vec3& pin_target,
    const State& state,
    Real g_max,
    Real k_bar,
    Real normal_epsilon,
    VecX& gradient) {

    Vec3 diff = state.positions[vertex_idx] - pin_target;
    Real gap = diff.norm();
    if (!in_domain(gap, g_max) || gap <= normal_epsilon) {
        return;
    }

    Vec3 n = diff / gap;
    Real dV = compute_gradient(gap, g_max, k_bar);
    gradient.segment<3>(vertex_idx * 3) += dV * n;
}

void Barrier::compute_pin_hessian(
    Index vertex_idx,
    const Vec3& pin_target,
    const State& state,
    Real g_max,
    Real k_bar,
    Real normal_epsilon,
    Real tolerance,
    std::vector<Triplet>& triplets) {

    Vec3 diff = state.positions[vertex_idx] - pin_target;
    Real gap = diff.norm();
    if (!in_domain(gap, g_max) || gap <= normal_epsilon) {
        return;
    }

    Vec3 n = diff / gap;
    Real dV = compute_gradient(gap, g_max, k_bar);
    Real d2V = compute_hessian(gap, g_max, k_bar);

    Mat3 Hessian = d2V * (n * n.transpose());
    Mat3 projector = Mat3::Identity() - n * n.transpose();
    Hessian += dV / gap * projector;

    int base = vertex_idx * 3;
    for (int r = 0; r < 3; ++r) {
        for (int c = 0; c < 3; ++c) {
            Real value = Hessian(r, c);
            if (std::abs(value) < tolerance) {
                continue;
            }
            triplets.emplace_back(base + r, base + c, value);
        }
    }
}

void Barrier::compute_wall_gradient(
    Index vertex_idx,
    const Vec3& wall_normal,
    Real wall_offset,
    const State& state,
    Real g_max,
    Real k_bar,
    Real normal_epsilon,
    VecX& gradient) {

    Vec3 n = normalize_or_default(wall_normal, normal_epsilon);
    Real gap = n.dot(state.positions[vertex_idx]) - wall_offset;
    if (!in_domain(gap, g_max)) {
        return;
    }

    Real dV = compute_gradient(gap, g_max, k_bar);
    gradient.segment<3>(vertex_idx * 3) += dV * n;
}

void Barrier::compute_wall_hessian(
    Index vertex_idx,
    const Vec3& wall_normal,
    Real wall_offset,
    const State& state,
    Real g_max,
    Real k_bar,
    Real normal_epsilon,
    Real tolerance,
    std::vector<Triplet>& triplets) {

    Vec3 n = normalize_or_default(wall_normal, normal_epsilon);
    Real gap = n.dot(state.positions[vertex_idx]) - wall_offset;
    if (!in_domain(gap, g_max)) {
        return;
    }

    Real d2V = compute_hessian(gap, g_max, k_bar);
    Mat3 Hessian = d2V * (n * n.transpose());

    int base = vertex_idx * 3;
    for (int r = 0; r < 3; ++r) {
        for (int c = 0; c < 3; ++c) {
            Real value = Hessian(r, c);
            if (std::abs(value) < tolerance) {
                continue;
            }
            triplets.emplace_back(base + r, base + c, value);
        }
    }
}

} // namespace ando_barrier
