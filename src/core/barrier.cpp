#include "barrier.h"
#include <cmath>
#include <algorithm>
#include <limits>

namespace ando_barrier {

Real Barrier::compute_energy(Real g, Real g_max, Real k) {
    if (g >= g_max || g <= 0.0) return 0.0;
    
    // V_weak(g, ḡ, k) = -(k/2)(g-ḡ)² ln(g/ḡ)
    Real diff = g - g_max;
    Real g_safe = std::max(g, Real(1e-12));
    Real ln_ratio = std::log(g_safe / g_max);
    
    return -0.5 * k * diff * diff * ln_ratio;
}

Real Barrier::compute_gradient(Real g, Real g_max, Real k) {
    if (g >= g_max || g <= 0.0) return 0.0;
    
    // d/dg V_weak = -k * (g - ḡ) * ln(g/ḡ) - k/2 * (g - ḡ)² / g
    Real diff = g - g_max;
    Real g_safe = std::max(g, Real(1e-12));
    Real ln_ratio = std::log(g_safe / g_max);
    
    return -k * diff * ln_ratio - 0.5 * k * diff * diff / g;
}

Real Barrier::compute_hessian(Real g, Real g_max, Real k) {
    if (g >= g_max || g <= 0.0) return 0.0;
    
    // d²/dg² V_weak = -k·ln(g/ḡ) - 2k(g-ḡ)/g + (k/2)(g-ḡ)²/g²
    Real diff = g - g_max;
    Real g_safe = std::max(g, Real(1e-12));
    Real ln_ratio = std::log(g_safe / g_max);

    return -k * ln_ratio - 2.0 * k * diff / g_safe + 0.5 * k * diff * diff / (g_safe * g_safe);
}

bool Barrier::in_domain(Real g, Real g_max) {
    return g > 0.0 && g < g_max;
}

// Compute gap gradient ∂g/∂x for point-triangle contact
// Gap function: g = ||p - q|| where q is closest point on triangle
void Barrier::compute_gap_gradient_point_triangle(
    const Vec3& p, const Vec3& a, const Vec3& b, const Vec3& c,
    const Vec3& normal, Real gap,
    Vec3 grad[4]) {
    
    // For a point-triangle contact with normal n and distance g:
    // ∂g/∂p = n (gradient w.r.t. point)
    // ∂g/∂{a,b,c} = -barycentric_weights * n (gradient w.r.t. triangle vertices)
    
    // The gradient of gap w.r.t. point position
    grad[0] = normal;
    
    // For triangle vertices, we need to compute barycentric coordinates
    // of the witness point q on the triangle
    Vec3 ab = b - a;
    Vec3 ac = c - a;
    Vec3 aq = p - gap * normal - a;  // q = p - g*n
    
    // Compute barycentric coordinates via projection
    Real d00 = ab.dot(ab);
    Real d01 = ab.dot(ac);
    Real d11 = ac.dot(ac);
    Real d20 = aq.dot(ab);
    Real d21 = aq.dot(ac);
    
    Real denom = d00 * d11 - d01 * d01;
    Real v = 0.0, w = 0.0;

    if (std::abs(denom) > 1e-10) {
        v = (d11 * d20 - d01 * d21) / denom;
        w = (d00 * d21 - d01 * d20) / denom;
    }

    // Clamp to valid barycentric range
    v = std::clamp(v, Real(0.0), Real(1.0));
    w = std::clamp(w, Real(0.0), Real(1.0));
    if (v + w > 1.0) {
        Real sum = v + w;
        v /= sum;
        w /= sum;
    }
    Real u = 1.0 - v - w;
    
    // Gradients for triangle vertices (negative of weighted normal)
    grad[1] = -u * normal;
    grad[2] = -v * normal;
    grad[3] = -w * normal;
}

// Contact gradient: ∂V/∂x = (∂V/∂g)(∂g/∂x)
void Barrier::compute_contact_gradient(
    const ContactPair& contact,
    const State& state,
    Real g_max,
    Real k_bar,
    VecX& gradient) {
    
    if (!in_domain(contact.gap, g_max)) return;
    
    // Scalar gradient ∂V/∂g
    Real dV_dg = compute_gradient(contact.gap, g_max, k_bar);
    
    // Gap gradients ∂g/∂x for each vertex
    Vec3 gap_grads[4];
    
    if (contact.type == ContactType::POINT_TRIANGLE) {
        const Vec3& p = state.positions[contact.idx0];
        const Vec3& a = state.positions[contact.idx1];
        const Vec3& b = state.positions[contact.idx2];
        const Vec3& c = state.positions[contact.idx3];

        Vec3 normal = contact.normal;
        Real n_norm = normal.norm();
        if (n_norm > Real(1e-9)) {
            normal /= n_norm;
        } else {
            normal = Vec3(0.0, 1.0, 0.0);
        }

        compute_gap_gradient_point_triangle(p, a, b, c, normal,
                                           contact.gap, gap_grads);
        
        // Add contributions: ∂V/∂x_i = (∂V/∂g)(∂g/∂x_i)
        gradient.segment<3>(contact.idx0 * 3) += dV_dg * gap_grads[0];
        gradient.segment<3>(contact.idx1 * 3) += dV_dg * gap_grads[1];
        gradient.segment<3>(contact.idx2 * 3) += dV_dg * gap_grads[2];
        gradient.segment<3>(contact.idx3 * 3) += dV_dg * gap_grads[3];
    }
    else if (contact.type == ContactType::EDGE_EDGE) {
        // For edge-edge: gradient is along the contact normal direction
        // Vertices on edge 0 get +n, vertices on edge 1 get -n
        Vec3 normal = contact.normal;
        Real n_norm = normal.norm();
        if (n_norm > Real(1e-9)) {
            normal /= n_norm;
        } else {
            normal = Vec3(0.0, 1.0, 0.0);
        }

        Vec3 force = dV_dg * normal;
        gradient.segment<3>(contact.idx0 * 3) += force * 0.5;
        gradient.segment<3>(contact.idx1 * 3) += force * 0.5;
        gradient.segment<3>(contact.idx2 * 3) -= force * 0.5;
        gradient.segment<3>(contact.idx3 * 3) -= force * 0.5;
    }
}

void Barrier::compute_rigid_contact_gradient(
    const ContactPair& contact,
    Real g_max,
    Real k_bar,
    VecX& gradient) {

    if (!in_domain(contact.gap, g_max)) return;

    Vec3 normal = contact.normal;
    Real norm = normal.norm();
    if (norm > Real(1e-9)) {
        normal /= norm;
    } else {
        normal = Vec3(0.0, 1.0, 0.0);
    }

    Real dV_dg = compute_gradient(contact.gap, g_max, k_bar);
    gradient.segment<3>(contact.idx0 * 3) += dV_dg * normal;
}

// Compute gap Hessian for point-triangle
void Barrier::compute_gap_hessian_point_triangle(
    const Vec3& p, const Vec3& a, const Vec3& b, const Vec3& c,
    const Vec3& normal, Real gap,
    Mat3 hess[4][4]) {
    
    // Constant normal approximation for small gaps (Section 3.2)
    // Full Hessian would require ∂²g/∂x² with curvature terms
    // Simplified: ∂²g/∂x² ≈ 0 when normal is approximately constant
    
    // Zero out all blocks
    for (int i = 0; i < 4; ++i) {
        for (int j = 0; j < 4; ++j) {
            hess[i][j].setZero();
        }
    }
}

void Barrier::compute_rigid_contact_hessian(
    const ContactPair& contact,
    Real g_max,
    Real k_bar,
    std::vector<Triplet>& triplets) {

    if (!in_domain(contact.gap, g_max)) return;

    Vec3 normal = contact.normal;
    Real norm = normal.norm();
    if (norm > Real(1e-9)) {
        normal /= norm;
    } else {
        normal = Vec3(0.0, 1.0, 0.0);
    }

    Real d2V_dg2 = compute_hessian(contact.gap, g_max, k_bar);
    Mat3 H = d2V_dg2 * (normal * normal.transpose());

    Index idx = contact.idx0;
    for (int i = 0; i < 3; ++i) {
        for (int j = 0; j < 3; ++j) {
            Real val = H(i, j);
            if (std::abs(val) > 1e-12) {
                triplets.emplace_back(3 * idx + i, 3 * idx + j, val);
            }
        }
    }
}

// Contact Hessian: ∂²V/∂x² = (∂²V/∂g²)(∂g/∂x)(∂g/∂x)ᵀ + (∂V/∂g)(∂²g/∂x²)
void Barrier::compute_contact_hessian(
    const ContactPair& contact,
    const State& state,
    Real g_max,
    Real k_bar,
    std::vector<Triplet>& triplets) {
    
    if (!in_domain(contact.gap, g_max)) return;
    
    // Scalar derivatives
    Real dV_dg = compute_gradient(contact.gap, g_max, k_bar);
    Real d2V_dg2 = compute_hessian(contact.gap, g_max, k_bar);
    
    // Gap gradients
    Vec3 gap_grads[4];
    Mat3 gap_hess[4][4];
    
    if (contact.type == ContactType::POINT_TRIANGLE) {
        const Vec3& p = state.positions[contact.idx0];
        const Vec3& a = state.positions[contact.idx1];
        const Vec3& b = state.positions[contact.idx2];
        const Vec3& c = state.positions[contact.idx3];

        Vec3 normal = contact.normal;
        Real n_norm = normal.norm();
        if (n_norm > Real(1e-9)) {
            normal /= n_norm;
        } else {
            normal = Vec3(0.0, 1.0, 0.0);
        }

        compute_gap_gradient_point_triangle(p, a, b, c, normal,
                                           contact.gap, gap_grads);
        compute_gap_hessian_point_triangle(p, a, b, c, normal,
                                          contact.gap, gap_hess);
        
        // Build 12×12 Hessian block: ∂²V/∂x² = (∂²V/∂g²)(∂g/∂x)(∂g/∂x)ᵀ + (∂V/∂g)(∂²g/∂x²)
        Index indices[4] = {contact.idx0, contact.idx1, contact.idx2, contact.idx3};
        
        for (int i = 0; i < 4; ++i) {
            for (int j = 0; j < 4; ++j) {
                // First term: (∂²V/∂g²)(∂g/∂x_i)(∂g/∂x_j)ᵀ
                Mat3 H_ij = d2V_dg2 * gap_grads[i] * gap_grads[j].transpose();

                // Second term: (∂V/∂g)(∂²g/∂x_i∂x_j)
                H_ij += dV_dg * gap_hess[i][j];

                // Add to sparse matrix using triplet insertion
                for (int row = 0; row < 3; ++row) {
                    for (int col = 0; col < 3; ++col) {
                        Real value = H_ij(row, col);
                        if (std::abs(value) < Real(1e-12)) continue;
                        int global_row = indices[i] * 3 + row;
                        int global_col = indices[j] * 3 + col;
                        triplets.emplace_back(global_row, global_col, value);
                    }
                }
            }
        }
    }
}

// Pin constraint: gap = ||x_i - p_target||
void Barrier::compute_pin_gradient(
    Index vertex_idx,
    const Vec3& pin_target,
    const State& state,
    Real g_max,
    Real k_bar,
    VecX& gradient) {
    
    Vec3 diff = state.positions[vertex_idx] - pin_target;
    Real gap = diff.norm();
    
    if (!in_domain(gap, g_max) || gap < 1e-10) return;
    
    // ∂g/∂x = (x - p_target) / ||x - p_target||
    Vec3 gap_grad = diff / gap;
    
    // ∂V/∂x = (∂V/∂g)(∂g/∂x)
    Real dV_dg = compute_gradient(gap, g_max, k_bar);
    gradient.segment<3>(vertex_idx * 3) += dV_dg * gap_grad;
}

void Barrier::compute_pin_hessian(
    Index vertex_idx,
    const Vec3& pin_target,
    const State& state,
    Real g_max,
    Real k_bar,
    std::vector<Triplet>& triplets) {
    
    Vec3 diff = state.positions[vertex_idx] - pin_target;
    Real gap = diff.norm();
    
    if (!in_domain(gap, g_max) || gap < 1e-10) return;
    
    Vec3 n = diff / gap;  // Normal direction
    
    // ∂²V/∂x² = (∂²V/∂g²)(∂g/∂x)(∂g/∂x)ᵀ + (∂V/∂g)(∂²g/∂x²)
    Real dV_dg = compute_gradient(gap, g_max, k_bar);
    Real d2V_dg2 = compute_hessian(gap, g_max, k_bar);
    
    // ∂²g/∂x² = (I - n⊗n) / g for distance function
    Mat3 gap_hess = (Mat3::Identity() - n * n.transpose()) / gap;
    
    // Combine terms
    Mat3 H = d2V_dg2 * (n * n.transpose()) + dV_dg * gap_hess;
    
    // Add to sparse matrix
    int base = vertex_idx * 3;
    for (int row = 0; row < 3; ++row) {
        for (int col = 0; col < 3; ++col) {
            Real value = H(row, col);
            if (std::abs(value) < Real(1e-12)) continue;
            triplets.emplace_back(base + row, base + col, value);
        }
    }
}

// Wall constraint: gap = n·x - offset
void Barrier::compute_wall_gradient(
    Index vertex_idx,
    const Vec3& wall_normal,
    Real wall_offset,
    const State& state,
    Real g_max,
    Real k_bar,
    VecX& gradient) {
    
    Vec3 normal = wall_normal;
    Real n_norm = normal.norm();
    if (n_norm > Real(1e-9)) {
        normal /= n_norm;
    } else {
        normal = Vec3(0.0, 1.0, 0.0);
    }

    Real gap = normal.dot(state.positions[vertex_idx]) - wall_offset;

    if (!in_domain(gap, g_max)) return;

    // ∂g/∂x = n (wall normal)
    // ∂V/∂x = (∂V/∂g) * n
    Real dV_dg = compute_gradient(gap, g_max, k_bar);
    gradient.segment<3>(vertex_idx * 3) += dV_dg * normal;
}

void Barrier::compute_wall_hessian(
    Index vertex_idx,
    const Vec3& wall_normal,
    Real wall_offset,
    const State& state,
    Real g_max,
    Real k_bar,
    std::vector<Triplet>& triplets) {
    
    Vec3 normal = wall_normal;
    Real n_norm = normal.norm();
    if (n_norm > Real(1e-9)) {
        normal /= n_norm;
    } else {
        normal = Vec3(0.0, 1.0, 0.0);
    }

    Real gap = normal.dot(state.positions[vertex_idx]) - wall_offset;

    if (!in_domain(gap, g_max)) return;

    // For wall: ∂²g/∂x² = 0 (linear gap function)
    // So: ∂²V/∂x² = (∂²V/∂g²) * n⊗n
    Real d2V_dg2 = compute_hessian(gap, g_max, k_bar);
    Mat3 H = d2V_dg2 * (normal * normal.transpose());

    int base = vertex_idx * 3;
    for (int row = 0; row < 3; ++row) {
        for (int col = 0; col < 3; ++col) {
            Real value = H(row, col);
            if (std::abs(value) < Real(1e-12)) continue;
            triplets.emplace_back(base + row, base + col, value);
        }
    }
}

} // namespace ando_barrier
