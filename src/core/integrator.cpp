#include "integrator.h"
#include "elasticity.h"
#include "barrier.h"
#include "stiffness.h"
#include "strain_limiting.h"
#include "friction.h"
#include "line_search.h"
#include "pcg_solver.h"
#include "matrix_assembly.h"
#include <iostream>
#include <algorithm>

namespace ando_barrier {

namespace {

// Helper struct to hold friction computation results for a single contact
struct FrictionData {
    Vec3 tangential;
    Real tangential_norm;
    Real k_friction;
    bool should_apply;
};

// Compute friction data for a contact. Returns false if friction should not be applied.
// This helper extracts the duplicated friction stiffness computation from both
// compute_gradient and assemble_system_matrix.
bool compute_friction_data(
    const ContactPair& contact,
    const State& state,
    Real dt,
    const SparseMatrix& H_base,
    const SparseMatrix& H_elastic,
    const SimParams& params,
    FrictionData& out
) {
    // Extract tangential motion
    out.tangential = FrictionModel::extract_tangential(
        state.positions[contact.idx0] - state.positions_prev[contact.idx0],
        contact.normal
    );
    
    out.tangential_norm = out.tangential.norm();
    if (!FrictionModel::should_apply_friction(out.tangential,
                                              params.friction_tangent_threshold)) {
        out.should_apply = false;
        return false;
    }
    
    // Estimate normal force from contact stiffness and gap
    Real k_contact = Stiffness::compute_contact_stiffness(
        contact, state, dt, H_elastic
    );
    Real normal_force_estimate = k_contact * std::abs(contact.gap);
    
    // Compute friction stiffness
    out.k_friction = FrictionModel::compute_friction_stiffness(
        normal_force_estimate,
        params.friction_mu,
        params.friction_epsilon,
        out.tangential_norm
    );
    
    out.should_apply = true;
    return true;
}

} // namespace

void Integrator::step(Mesh& mesh, State& state, Constraints& constraints,
                     const SimParams& params,
                     std::vector<RigidBody>* rigid_bodies) {

    const int n = static_cast<int>(state.num_vertices());
    const Real dt = params.dt;
    
    // Cache initial positions for velocity update (Section 3.6)
    VecX x_old;
    state.flatten_positions(x_old);
    
    // 1. Predict positions: x̂ = x + dt*v (forward Euler prediction)
    VecX x_target;
    state.flatten_positions(x_target);
    
    VecX v_flat = VecX::Zero(3 * n);
    for (int i = 0; i < n; ++i) {
        v_flat[3*i]   = state.velocities[i][0];
        v_flat[3*i+1] = state.velocities[i][1];
        v_flat[3*i+2] = state.velocities[i][2];
    }
    
    x_target += dt * v_flat;
    
    // 2. Detect collisions
    std::vector<ContactPair> contacts;
    detect_collisions(mesh, state, contacts, rigid_bodies);
    
    // 3. β accumulation loop (Section 3.6)
    Real beta = 0.0;
    int beta_iter = 0;
    const int max_beta_iters = 20;
    
    while (beta < params.beta_max && beta_iter < max_beta_iters) {
        Real alpha = inner_newton_step(mesh, state, x_target, contacts,
                                      constraints, params, beta, rigid_bodies);
        
        // Update β: β ← β + (1 - β) α
        beta = beta + (1.0 - beta) * alpha;
        
        beta_iter++;
        
        if (alpha < 1e-6) {
            std::cerr << "Line search failed, stopping β accumulation" << std::endl;
            break;
        }
    }
    
    // 4. Error reduction pass with full β
    if (beta > 1e-6) {
        inner_newton_step(mesh, state, x_target, contacts, constraints, params, beta, rigid_bodies);
    }
    
    // 5. Update velocities: v = (x_new - x_old) / (β Δt) (Section 3.6)
    if (beta > 1e-6) {
        VecX x_new;
        state.flatten_positions(x_new);
        VecX dx = x_new - x_old;

        Real beta_dt = beta * dt;
        for (int i = 0; i < n; ++i) {
            state.velocities[i] = Vec3(
                dx[3*i]   / beta_dt,
                dx[3*i+1] / beta_dt,
                dx[3*i+2] / beta_dt
            );
        }

        if (params.velocity_damping > 0.0) {
            apply_velocity_damping(state, params.velocity_damping);
        }

        if (params.contact_restitution > 0.0) {
            apply_contact_restitution(mesh, constraints, state, params, rigid_bodies);
        }
    }

    if (rigid_bodies && !rigid_bodies->empty()) {
        apply_rigid_coupling(mesh, state, *rigid_bodies, constraints, params);
    }
}

Real Integrator::inner_newton_step(
    const Mesh& mesh,
    State& state,
    const VecX& x_target,
    const std::vector<ContactPair>& contacts,
    Constraints& constraints,
    const SimParams& params,
    Real beta,
    std::vector<RigidBody>* rigid_bodies) {
    
    const int n = static_cast<int>(state.num_vertices());
    
    int max_newton_iters = params.max_newton_steps;
    if (params.enable_friction) {
        max_newton_iters = std::max(max_newton_iters, params.friction_min_newton_steps);
    }

    for (int newton_iter = 0; newton_iter < max_newton_iters; ++newton_iter) {
        // Compute gradient: g = ∇E
        VecX gradient = VecX::Zero(3 * n);
        compute_gradient(mesh, state, x_target, contacts, constraints, params, beta, gradient, rigid_bodies);
        
        // Check convergence
        VecX x_current;
        state.flatten_positions(x_current);
        Real grad_norm = gradient.lpNorm<Eigen::Infinity>();
        if (grad_norm < params.pcg_tol) {
            return 1.0;
        }
        
        // Assemble Hessian: H = ∇²E
        SparseMatrix hessian;
        assemble_system_matrix(mesh, state, contacts, constraints, params, beta, hessian, rigid_bodies);
        
        // Solve: H d = -g
        VecX direction = VecX::Zero(3 * n);
        VecX neg_gradient = -gradient;
        bool converged = PCGSolver::solve(hessian, neg_gradient, direction, 
                                         params.pcg_tol, params.pcg_max_iters);
        
        if (!converged) {
            std::cerr << "PCG did not converge in Newton iteration " << newton_iter << std::endl;
        }
        
        // Extract active pins for line search
        std::vector<Pin> pins_for_search;
        for (const auto& pin : constraints.pins) {
            if (pin.active) {
                pins_for_search.push_back(pin);
            }
        }
        
        // Extract first active wall for line search
        Vec3 wall_normal(0, 0, 0);
        Real wall_offset = 0.0;
        for (const auto& wall : constraints.walls) {
            if (wall.active) {
                wall_normal = wall.normal;
                wall_offset = wall.offset;
                break;
            }
        }
        
        // Line search with extended direction (Section 3.5)
        Real alpha = LineSearch::search(
            mesh, state, direction, contacts,
            pins_for_search, wall_normal, wall_offset,
            1.25
        );
        
        if (alpha < 1e-8) {
            return 0.0;
        }
        
        // Update positions: x ← x + α * extension * d
        VecX x_new = x_current + alpha * 1.25 * direction;
        state.unflatten_positions(x_new);
        
        if (alpha > 0.99) {
            return 1.0;
        }
    }
    
    return 0.5;
}

std::vector<ContactPair> Integrator::compute_contacts(const Mesh& mesh,
                                                     const State& state,
                                                     const std::vector<RigidBody>* rigid_bodies) {
    std::vector<ContactPair> contacts;
    detect_collisions(mesh, state, contacts, rigid_bodies);
    return contacts;
}

void Integrator::compute_gradient(
    const Mesh& mesh,
    const State& state,
    const VecX& x_target,
    const std::vector<ContactPair>& contacts,
    Constraints& constraints,
    const SimParams& params,
    Real beta,
    VecX& gradient,
    std::vector<RigidBody>* rigid_bodies) {

    const int n = static_cast<int>(state.num_vertices());
    const Real dt = params.dt;

    (void)rigid_bodies;
    
    // Flatten current positions
    VecX x_current;
    state.flatten_positions(x_current);
    
    // 1. Inertia term: (1/dt²) M (x - x̂)
    for (int i = 0; i < n; ++i) {
        Real mass = state.masses[i];
        Real mass_factor = mass / (dt * dt);
        
        for (int j = 0; j < 3; ++j) {
            gradient[3*i + j] += mass_factor * (x_current[3*i + j] - x_target[3*i + j]);
        }
    }
    
    // 2. Elastic forces: ∇E_elastic
    VecX elastic_gradient = VecX::Zero(3 * n);
    Elasticity::compute_gradient(mesh, state, elastic_gradient);
    gradient += elastic_gradient;
    
    // Assemble base elastic Hessian (mass + elasticity) for stiffness extraction
    SparseMatrix H_total;
    H_total.resize(3 * n, 3 * n);
    std::vector<Triplet> base_triplets;
    base_triplets.reserve(9 * n + 9 * mesh.triangles.size() * 9);
    
    // Mass/dt² diagonal
    Real dt2_inv = 1.0 / (dt * dt);
    for (int i = 0; i < n; ++i) {
        Real mass_factor = state.masses[i] * dt2_inv;
        for (int j = 0; j < 3; ++j) {
            base_triplets.push_back(Triplet(3*i + j, 3*i + j, mass_factor));
        }
    }
    
    // Elastic Hessian
    std::vector<Triplet> elastic_triplets;
    Elasticity::compute_hessian(mesh, state, elastic_triplets);
    base_triplets.insert(base_triplets.end(), elastic_triplets.begin(), elastic_triplets.end());
    H_total.setFromTriplets(base_triplets.begin(), base_triplets.end());

    SparseMatrix H_elastic;
    H_elastic.resize(3 * n, 3 * n);
    H_elastic.setFromTriplets(elastic_triplets.begin(), elastic_triplets.end());

    if (params.enable_strain_limiting) {
        StrainLimiting::rebuild_constraints(mesh, state, params, H_elastic, constraints);
        StrainLimiting::accumulate_gradient(mesh, state, constraints, params, gradient);
    } else {
        constraints.clear_strain_limits();
    }
    
    // 3. Barrier forces: Σ ∇V_barrier
    // For each contact
    for (const auto& contact : contacts) {
        if (contact.type == ContactType::POINT_TRIANGLE ||
            contact.type == ContactType::RIGID_POINT_TRIANGLE) {
            // Extract H_block for vertex involved in contact
            Mat3 H_block = Stiffness::extract_hessian_block(H_total, contact.idx0);
            Real k_bar = Stiffness::compute_contact_stiffness(
                contact, state, dt, H_elastic
            );

            if (contact.type == ContactType::POINT_TRIANGLE) {
                Barrier::compute_contact_gradient(contact,
                                                 params.contact_gap_max,
                                                 k_bar,
                                                 params.contact_normal_epsilon,
                                                 gradient);
            } else {
                Barrier::compute_rigid_contact_gradient(contact,
                                                        params.contact_gap_max,
                                                        k_bar,
                                                        params.contact_normal_epsilon,
                                                        gradient);
            }
        }
    }
    
    // 4. Pin and wall barrier gradients
    // Pins: gap = ||x_i - pin_target||
    for (const auto& pin : constraints.pins) {
        if (!pin.active) continue;

        Vec3 offset = state.positions[pin.vertex_idx] - pin.target_position;
        Mat3 H_block = Stiffness::extract_hessian_block(H_total, pin.vertex_idx);
        Real k_bar = Stiffness::compute_pin_stiffness(state.masses[pin.vertex_idx], dt,
                                                     offset, H_block, params.min_gap);

        Barrier::compute_pin_gradient(pin.vertex_idx, pin.target_position, state,
                                      params.contact_gap_max, k_bar,
                                      params.contact_normal_epsilon,
                                      gradient);
    }

    // Walls: linear gap function g = n·x - offset
    for (const auto& wall : constraints.walls) {
        if (!wall.active) continue;

        // For each vertex, compute wall stiffness and gradient contribution
        for (Index vi = 0; vi < static_cast<Index>(state.num_vertices()); ++vi) {
            Mat3 H_block = Stiffness::extract_hessian_block(H_total, vi);
            Real k_bar = Stiffness::compute_wall_stiffness(state.masses[vi], params.wall_gap,
                                                           wall.normal, H_block, params.min_gap);

            Barrier::compute_wall_gradient(vi, wall.normal, wall.offset, state,
                                           params.contact_gap_max, k_bar,
                                           params.contact_normal_epsilon,
                                           gradient);
        }
    }
    
    // 5. Friction forces (if enabled)
    if (params.enable_friction && params.friction_mu > 0.0) {
        for (const auto& contact : contacts) {
            FrictionData fric;
            if (!compute_friction_data(contact, state, dt, H_total, H_elastic, params, fric)) {
                continue;  // Skip stationary contacts
            }
            
            // Compute friction gradient (restoring force opposing tangential motion)
            Vec3 friction_grad = FrictionModel::compute_gradient(
                state.positions[contact.idx0],
                state.positions_prev[contact.idx0],
                contact.normal,
                fric.k_friction
            );
            
            // Add to gradient vector
            int idx = static_cast<int>(contact.idx0);
            gradient[3*idx + 0] += friction_grad[0];
            gradient[3*idx + 1] += friction_grad[1];
            gradient[3*idx + 2] += friction_grad[2];
        }
    }
}

void Integrator::assemble_system_matrix(
    const Mesh& mesh,
    const State& state,
    const std::vector<ContactPair>& contacts,
    Constraints& constraints,
    const SimParams& params,
    Real beta,
    SparseMatrix& hessian,
    std::vector<RigidBody>* rigid_bodies) {

    const int n = static_cast<int>(state.num_vertices());
    const Real dt = params.dt;

    (void)rigid_bodies;
    
    // Initialize sparse matrix
    hessian.resize(3 * n, 3 * n);
    hessian.setZero();
    
    MatrixAssembly& assembly = MatrixAssembly::instance();
    assembly.configure(3 * n);

    // Use triplet format for assembly
    std::vector<Triplet> triplets;
    triplets.reserve(9 * n + 9 * mesh.triangles.size() * 9);  // Estimate

    assembly.append_mass(state, dt, triplets);

    // 2. Elastic Hessian: H_elastic
    std::vector<Triplet> elastic_triplets;
    Elasticity::compute_hessian(mesh, state, elastic_triplets);

    assembly.append_elastic(elastic_triplets, triplets);
    
    // Build base Hessians for stiffness extraction
    SparseMatrix H_base;
    H_base.resize(3 * n, 3 * n);
    H_base.setFromTriplets(triplets.begin(), triplets.end());

    SparseMatrix H_elastic;
    H_elastic.resize(3 * n, 3 * n);
    H_elastic.setFromTriplets(elastic_triplets.begin(), elastic_triplets.end());

    if (params.enable_strain_limiting) {
        if (constraints.strain_limits.empty()) {
            StrainLimiting::rebuild_constraints(mesh, state, params, H_elastic, constraints);
        }
        StrainLimiting::accumulate_hessian(mesh, state, constraints, params, triplets);
    } else {
        constraints.clear_strain_limits();
    }
    
    // 3. Barrier Hessians: Σ H_barrier
    // For each contact
    for (const auto& contact : contacts) {
        if (contact.type == ContactType::POINT_TRIANGLE ||
            contact.type == ContactType::RIGID_POINT_TRIANGLE) {
            // Extract H_block for accurate stiffness
            Mat3 H_block = Stiffness::extract_hessian_block(H_base, contact.idx0);
            Real k_bar = Stiffness::compute_contact_stiffness(
                contact, state, dt, H_elastic
            );

            if (contact.type == ContactType::POINT_TRIANGLE) {
                Barrier::compute_contact_hessian(contact,
                                                 params.contact_gap_max,
                                                 k_bar,
                                                 params.contact_normal_epsilon,
                                                 params.barrier_tolerance,
                                                 triplets);
            } else {
                Barrier::compute_rigid_contact_hessian(contact,
                                                       params.contact_gap_max,
                                                       k_bar,
                                                       params.contact_normal_epsilon,
                                                       params.barrier_tolerance,
                                                       triplets);
            }
        }
    }

    // 4. Pin and wall Hessians
    // Pins
    for (const auto& pin : constraints.pins) {
        if (!pin.active) continue;

        // Extract H_block from base Hessian
        Mat3 H_block = Stiffness::extract_hessian_block(H_base, pin.vertex_idx);
        Real k_bar = Stiffness::compute_pin_stiffness(state.masses[pin.vertex_idx], dt,
                                                     state.positions[pin.vertex_idx] - pin.target_position,
                                                     H_block, params.min_gap);

        Barrier::compute_pin_hessian(pin.vertex_idx, pin.target_position, state,
                                     params.contact_gap_max, k_bar,
                                     params.contact_normal_epsilon,
                                     params.barrier_tolerance,
                                     triplets);
    }

    // Walls
    for (const auto& wall : constraints.walls) {
        if (!wall.active) continue;

        for (Index vi = 0; vi < static_cast<Index>(state.num_vertices()); ++vi) {
            Mat3 H_block = Stiffness::extract_hessian_block(H_base, vi);
            Real k_bar = Stiffness::compute_wall_stiffness(state.masses[vi], params.wall_gap,
                                                           wall.normal, H_block, params.min_gap);

            Barrier::compute_wall_hessian(vi, wall.normal, wall.offset, state,
                                          params.contact_gap_max, k_bar,
                                          params.contact_normal_epsilon,
                                          params.barrier_tolerance,
                                          triplets);
        }
    }

    // 5. Friction Hessians (if enabled)
    if (params.enable_friction && params.friction_mu > 0.0) {
        for (const auto& contact : contacts) {
            FrictionData fric;
            if (!compute_friction_data(contact, state, dt, H_base, H_elastic, params, fric)) {
                continue;  // Skip stationary contacts
            }
            
            // Compute friction Hessian (3×3 block for vertex)
            Mat3 friction_hess = FrictionModel::compute_hessian(contact.normal, fric.k_friction);
            
            // Add to triplets (diagonal block only, since friction is per-vertex)
            int idx = static_cast<int>(contact.idx0);
            for (int i = 0; i < 3; ++i) {
                for (int j = 0; j < 3; ++j) {
                    Real val = friction_hess(i, j);
                    if (std::abs(val) > 1e-12) {
                        triplets.push_back(Triplet(3*idx + i, 3*idx + j, val));
                    }
                }
            }
        }
    }
    
    // Build sparse matrix from triplets
    hessian.setFromTriplets(triplets.begin(), triplets.end());
    
    // Enforce symmetry
    SparseMatrix hessian_t = hessian.transpose();
    hessian = (hessian + hessian_t) * 0.5;
}

void Integrator::detect_collisions(const Mesh& mesh, const State& state,
                                  std::vector<ContactPair>& contacts,
                                  const std::vector<RigidBody>* rigid_bodies) {
    contacts.clear();
    if (rigid_bodies) {
        Collision::detect_all_collisions(mesh, state, *rigid_bodies, contacts);
    } else {
        Collision::detect_all_collisions(mesh, state, contacts);
    }
}

void Integrator::apply_velocity_damping(State& state, Real damping_factor) {
    Real clamped = std::clamp(damping_factor, Real(0.0), Real(1.0));
    Real scale = Real(1.0) - clamped;
    for (auto& v : state.velocities) {
        v *= scale;
    }
}

void Integrator::apply_contact_restitution(const Mesh& mesh,
                                          const Constraints& constraints,
                                          State& state,
                                          const SimParams& params,
                                          std::vector<RigidBody>* rigid_bodies) {
    Real restitution = std::clamp(params.contact_restitution, Real(0.0), Real(1.0));
    if (restitution <= Real(0.0)) {
        return;
    }

    auto apply_impulse = [&](Index idx, const Vec3& normal) {
        if (idx < 0 || static_cast<size_t>(idx) >= state.velocities.size()) {
            return;
        }
        Vec3 n = normal;
        Real norm = n.norm();
        if (norm < Real(1e-8)) {
            return;
        }
        n /= norm;
        Vec3& vel = state.velocities[idx];
        Real vn = vel.dot(n);
        if (vn < Real(0.0)) {
            vel -= (Real(1.0) + restitution) * vn * n;
        }
    };

    std::vector<ContactPair> contacts;
    if (rigid_bodies) {
        Collision::detect_all_collisions(mesh, state, *rigid_bodies, contacts);
    } else {
        Collision::detect_all_collisions(mesh, state, contacts);
    }

    Real gap_limit = std::max(params.contact_gap_max, Real(1e-5));
    for (const auto& contact : contacts) {
        if (contact.gap > gap_limit) {
            continue;
        }

        if (contact.type == ContactType::POINT_TRIANGLE) {
            apply_impulse(contact.idx0, contact.normal);
        } else if (contact.type == ContactType::EDGE_EDGE) {
            apply_impulse(contact.idx0, contact.normal);
            apply_impulse(contact.idx1, contact.normal);
            apply_impulse(contact.idx2, -contact.normal);
            apply_impulse(contact.idx3, -contact.normal);
        } else if (contact.type == ContactType::WALL) {
            apply_impulse(contact.idx0, contact.normal);
        } else if (contact.type == ContactType::RIGID_POINT_TRIANGLE && rigid_bodies &&
                   contact.rigid_body_index >= 0 &&
                   contact.rigid_body_index < static_cast<int>(rigid_bodies->size())) {
            Vec3 normal = contact.normal;
            Real norm = normal.norm();
            if (norm < Real(1e-8)) {
                continue;
            }
            normal /= norm;

            Index vidx = contact.idx0;
            if (vidx < 0 || static_cast<size_t>(vidx) >= state.velocities.size()) {
                continue;
            }

            RigidBody& body = (*rigid_bodies)[contact.rigid_body_index];

            Vec3 vertex_velocity = state.velocities[vidx];
            Vec3 body_velocity = body.velocity_at_point(contact.witness_q);
            Vec3 relative = vertex_velocity - body_velocity;
            Real vn = relative.dot(normal);
            if (vn >= Real(0.0)) {
                continue;
            }

            Real inv_mass = state.masses[vidx] > Real(0.0) ? Real(1.0) / state.masses[vidx] : Real(0.0);
            Vec3 r = contact.witness_q - body.position();
            Vec3 cross = r.cross(normal);
            Real angular_term = cross.dot(body.inertia_world_inv() * cross);
            Real denom = inv_mass + angular_term;
            if (denom <= Real(0.0)) {
                continue;
            }

            Real j = -(Real(1.0) + restitution) * vn / denom;
            Vec3 impulse = j * normal;

            vertex_velocity += impulse * inv_mass;
            state.velocities[vidx] = vertex_velocity;
            body.apply_impulse(contact.witness_q, -impulse);
        }
    }

    for (const auto& wall : constraints.walls) {
        if (!wall.active) {
            continue;
        }
        Vec3 normal = wall.normal;
        Real norm = normal.norm();
        if (norm < Real(1e-8)) {
            continue;
        }
        normal /= norm;
        for (size_t i = 0; i < state.positions.size(); ++i) {
            Real signed_distance = normal.dot(state.positions[i]) - wall.offset;
            if (signed_distance <= wall.gap + params.contact_gap_max) {
                apply_impulse(static_cast<Index>(i), normal);
            }
        }
    }
}

void Integrator::apply_rigid_coupling(const Mesh& mesh,
                                     const State& state,
                                     std::vector<RigidBody>& rigid_bodies,
                                     const Constraints& constraints,
                                     const SimParams& params) {
    if (rigid_bodies.empty()) {
        return;
    }

    (void)constraints;

    std::vector<ContactPair> contacts;
    Collision::detect_all_collisions(mesh, state, rigid_bodies, contacts);

    const int n = static_cast<int>(state.num_vertices());
    const Real dt = params.dt;

    // Assemble base Hessians for stiffness extraction (mass + elasticity)
    SparseMatrix H_total;
    H_total.resize(3 * n, 3 * n);
    std::vector<Triplet> base_triplets;
    base_triplets.reserve(9 * n + 9 * mesh.triangles.size() * 9);

    Real dt2_inv = 1.0 / (dt * dt);
    for (int i = 0; i < n; ++i) {
        Real mass_factor = state.masses[i] * dt2_inv;
        for (int j = 0; j < 3; ++j) {
            base_triplets.emplace_back(3 * i + j, 3 * i + j, mass_factor);
        }
    }

    std::vector<Triplet> elastic_triplets;
    Elasticity::compute_hessian(mesh, state, elastic_triplets);
    base_triplets.insert(base_triplets.end(), elastic_triplets.begin(), elastic_triplets.end());
    H_total.setFromTriplets(base_triplets.begin(), base_triplets.end());

    SparseMatrix H_elastic;
    H_elastic.resize(3 * n, 3 * n);
    H_elastic.setFromTriplets(elastic_triplets.begin(), elastic_triplets.end());

    for (auto& body : rigid_bodies) {
        body.clear_accumulators();
    }

    for (const auto& contact : contacts) {
        if (contact.type != ContactType::RIGID_POINT_TRIANGLE) {
            continue;
        }
        if (contact.rigid_body_index < 0 ||
            contact.rigid_body_index >= static_cast<int>(rigid_bodies.size())) {
            continue;
        }

        Mat3 H_block = Stiffness::extract_hessian_block(H_total, contact.idx0);
        Real k_bar = Stiffness::compute_contact_stiffness(
            contact, state, dt, H_elastic
        );

        Vec3 normal = contact.normal;
        Real norm = normal.norm();
        if (norm < Real(1e-8)) {
            continue;
        }
        normal /= norm;

        Real dV_dg = Barrier::compute_gradient(contact.gap, params.contact_gap_max, k_bar);
        if (std::abs(dV_dg) < Real(1e-12)) {
            continue;
        }

        Vec3 force = dV_dg * normal;
        RigidBody& body = rigid_bodies[contact.rigid_body_index];
        body.apply_force(contact.witness_q, -force, Real(0.0));
    }

    for (auto& body : rigid_bodies) {
        body.integrate(params.dt);
    }
}

} // namespace ando_barrier
