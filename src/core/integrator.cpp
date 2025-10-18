#include "integrator.h"
#include "elasticity.h"
#include "barrier.h"
#include "stiffness.h"
#include "line_search.h"
#include "pcg_solver.h"
#include <iostream>
#include <algorithm>

namespace ando_barrier {

void Integrator::step(Mesh& mesh, State& state, Constraints& constraints,
                     const SimParams& params) {
    
    const int n = static_cast<int>(state.num_vertices());
    const Real dt = params.dt;
    
    // Cache initial positions for velocity update (Section 3.6)
    VecX x_old;
    state.flatten_positions(x_old);
    
    // 1. Predict positions: x̂ = x + dt*v (simple forward Euler prediction)
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
    detect_collisions(mesh, state, contacts);
    
    // 3. β accumulation loop
    Real beta = 0.0;
    int beta_iter = 0;
    const int max_beta_iters = 20;  // Maximum β iterations
    
    while (beta < params.beta_max && beta_iter < max_beta_iters) {
        // Inner Newton step
        Real alpha = inner_newton_step(mesh, state, x_target, contacts,
                                      constraints, params, beta);
        
        // Update β: β ← β + (1 - β) α
        beta = beta + (1.0 - beta) * alpha;
        
        beta_iter++;
        
        // If step was rejected (α ≈ 0), break
        if (alpha < 1e-6) {
            std::cerr << "Line search failed, stopping β accumulation" << std::endl;
            break;
        }
    }
    
    // 4. Error reduction pass: one more Newton step with full β
    if (beta > 1e-6) {
        inner_newton_step(mesh, state, x_target, contacts, constraints, params, beta);
    }
    
    // 5. Update velocities: v = (x_new - x_old) / (β Δt) (Section 3.6)
    // Note: x_old cached before integration, x_new is current state after Newton steps
    if (beta > 1e-6) {
        VecX x_new;
        state.flatten_positions(x_new);
        VecX dx = x_new - x_old;  // Actual displacement from initial position
        
        Real beta_dt = beta * dt;
        for (int i = 0; i < n; ++i) {
            state.velocities[i] = Vec3(
                dx[3*i]   / beta_dt,
                dx[3*i+1] / beta_dt,
                dx[3*i+2] / beta_dt
            );
        }
    }
}

Real Integrator::inner_newton_step(
    const Mesh& mesh,
    State& state,
    const VecX& x_target,
    const std::vector<ContactPair>& contacts,
    const Constraints& constraints,
    const SimParams& params,
    Real beta) {
    
    const int n = static_cast<int>(state.num_vertices());
    
    // Newton iterations
    for (int newton_iter = 0; newton_iter < params.max_newton_steps; ++newton_iter) {
        // Compute gradient (RHS): g = ∇E
        VecX gradient = VecX::Zero(3 * n);
        compute_gradient(mesh, state, x_target, contacts, constraints, params, beta, gradient);
        
        // Check convergence
        VecX x_current;
        state.flatten_positions(x_current);
        Real grad_norm = gradient.lpNorm<Eigen::Infinity>();
        if (grad_norm < params.pcg_tol) {
            return 1.0;  // Converged, full step accepted
        }
        
        // Assemble system matrix (Hessian): H = ∇²E
        SparseMatrix hessian;
        assemble_system_matrix(mesh, state, contacts, constraints, params, beta, hessian);
        
        // Solve: H d = -g
        VecX direction = VecX::Zero(3 * n);
        VecX neg_gradient = -gradient;
        bool converged = PCGSolver::solve(hessian, neg_gradient, direction, 
                                         params.pcg_tol, params.pcg_max_iters);
        
        if (!converged) {
            std::cerr << "PCG did not converge in Newton iteration " << newton_iter << std::endl;
        }
        
        // Extract active pins from constraints
        std::vector<Pin> pins_for_search;
        for (const auto& pin : constraints.pins) {
            if (pin.active) {
                pins_for_search.push_back(pin);
            }
        }
        
        // Extract wall from constraints (use first active wall)
        Vec3 wall_normal(0, 0, 0);
        Real wall_offset = 0.0;
        for (const auto& wall : constraints.walls) {
            if (wall.active) {
                wall_normal = wall.normal;
                wall_offset = wall.offset;
                break;  // Use first active wall
            }
        }
        
        // Line search for feasible α
        Real alpha = LineSearch::search(
            mesh, state, direction, contacts,
            pins_for_search, wall_normal, wall_offset,
            1.25  // Extended direction
        );
        
        if (alpha < 1e-8) {
            return 0.0;  // Line search failed
        }
        
        // Update positions: x ← x + α * extension * d
        VecX x_new = x_current + alpha * 1.25 * direction;
        state.unflatten_positions(x_new);
        
        // If we took a full step, we're done
        if (alpha > 0.99) {
            return 1.0;
        }
    }
    
    // Max Newton iterations reached
    return 0.5;  // Partial success
}

std::vector<ContactPair> Integrator::compute_contacts(const Mesh& mesh,
                                                     const State& state) {
    std::vector<ContactPair> contacts;
    detect_collisions(mesh, state, contacts);
    return contacts;
}

void Integrator::compute_gradient(
    const Mesh& mesh,
    const State& state,
    const VecX& x_target,
    const std::vector<ContactPair>& contacts,
    const Constraints& constraints,
    const SimParams& params,
    Real beta,
    VecX& gradient) {
    
    const int n = static_cast<int>(state.num_vertices());
    const Real dt = params.dt;
    
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
    SparseMatrix H_elastic;
    H_elastic.resize(3 * n, 3 * n);
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
    H_elastic.setFromTriplets(base_triplets.begin(), base_triplets.end());
    
    // 3. Barrier forces: Σ ∇V_barrier
    // For each contact
    for (const auto& contact : contacts) {
        if (contact.type == ContactType::POINT_TRIANGLE) {
            // Extract H_block for vertex involved in contact
            Mat3 H_block = Stiffness::extract_hessian_block(H_elastic, contact.idx0);
            Real k_bar = Stiffness::compute_contact_stiffness(
                state.masses[contact.idx0], dt, contact.gap, contact.normal, H_block
            );
            
            // Add barrier gradient
            Barrier::compute_contact_gradient(contact, state, 
                                             params.contact_gap_max, k_bar, gradient);
        }
    }
    
    // 4. Pin and wall barrier gradients
    // Pins: gap = ||x_i - pin_target||
    for (const auto& pin : constraints.pins) {
        if (!pin.active) continue;

        Vec3 offset = state.positions[pin.vertex_idx] - pin.target_position;
        Mat3 H_block = Stiffness::extract_hessian_block(H_elastic, pin.vertex_idx);
        Real k_bar = Stiffness::compute_pin_stiffness(state.masses[pin.vertex_idx], dt, offset, H_block);

        Barrier::compute_pin_gradient(pin.vertex_idx, pin.target_position, state,
                                      params.contact_gap_max, k_bar, gradient);
    }

    // Walls: linear gap function g = n·x - offset
    for (const auto& wall : constraints.walls) {
        if (!wall.active) continue;

        // For each vertex, compute wall stiffness and gradient contribution
        for (Index vi = 0; vi < static_cast<Index>(state.num_vertices()); ++vi) {
            Mat3 H_block = Stiffness::extract_hessian_block(H_elastic, vi);
            Real k_bar = Stiffness::compute_wall_stiffness(state.masses[vi], params.wall_gap, wall.normal, H_block);

            Barrier::compute_wall_gradient(vi, wall.normal, wall.offset, state,
                                           params.contact_gap_max, k_bar, gradient);
        }
    }
}

void Integrator::assemble_system_matrix(
    const Mesh& mesh,
    const State& state,
    const std::vector<ContactPair>& contacts,
    const Constraints& constraints,
    const SimParams& params,
    Real beta,
    SparseMatrix& hessian) {
    
    const int n = static_cast<int>(state.num_vertices());
    const Real dt = params.dt;
    
    // Initialize sparse matrix
    hessian.resize(3 * n, 3 * n);
    hessian.setZero();
    
    // Use triplet format for assembly
    std::vector<Triplet> triplets;
    triplets.reserve(9 * n + 9 * mesh.triangles.size() * 9);  // Estimate
    
    // 1. Mass/dt² diagonal blocks
    Real dt2_inv = 1.0 / (dt * dt);
    for (int i = 0; i < n; ++i) {
        Real mass = state.masses[i];
        Real mass_factor = mass * dt2_inv;
        
        for (int j = 0; j < 3; ++j) {
            triplets.push_back(Triplet(3*i + j, 3*i + j, mass_factor));
        }
    }
    
    // 2. Elastic Hessian: H_elastic
    std::vector<Triplet> elastic_triplets;
    Elasticity::compute_hessian(mesh, state, elastic_triplets);
    
    // Add elastic Hessian triplets
    triplets.insert(triplets.end(), elastic_triplets.begin(), elastic_triplets.end());
    
    // Build a temporary base Hessian (mass + elasticity) for stiffness extraction
    SparseMatrix H_base;
    H_base.resize(3 * n, 3 * n);
    H_base.setFromTriplets(triplets.begin(), triplets.end());
    
    // 3. Barrier Hessians: Σ H_barrier
    // For each contact
    for (const auto& contact : contacts) {
        if (contact.type == ContactType::POINT_TRIANGLE) {
            // Extract H_block for accurate stiffness
            Mat3 H_block = Stiffness::extract_hessian_block(H_base, contact.idx0);
            Real k_bar = Stiffness::compute_contact_stiffness(
                state.masses[contact.idx0], dt, contact.gap, contact.normal, H_block
            );
            
            // Add barrier Hessian (will be sparse, 4×4 block of 3×3 matrices)
            SparseMatrix barrier_hessian;
            Barrier::compute_contact_hessian(contact, state,
                                            params.contact_gap_max, k_bar,
                                            barrier_hessian);
            
            // Add barrier Hessian triplets
            for (int k = 0; k < barrier_hessian.outerSize(); ++k) {
                for (SparseMatrix::InnerIterator it(barrier_hessian, k); it; ++it) {
                    triplets.push_back(Triplet(it.row(), it.col(), it.value()));
                }
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
                                                     H_block);

        SparseMatrix pin_hess;
        Barrier::compute_pin_hessian(pin.vertex_idx, pin.target_position, state,
                                     params.contact_gap_max, k_bar, pin_hess);

        for (int k = 0; k < pin_hess.outerSize(); ++k) {
            for (SparseMatrix::InnerIterator it(pin_hess, k); it; ++it) {
                triplets.push_back(Triplet(it.row(), it.col(), it.value()));
            }
        }
    }

    // Walls
    for (const auto& wall : constraints.walls) {
        if (!wall.active) continue;

        for (Index vi = 0; vi < static_cast<Index>(state.num_vertices()); ++vi) {
            Mat3 H_block = Stiffness::extract_hessian_block(H_base, vi);
            Real k_bar = Stiffness::compute_wall_stiffness(state.masses[vi], params.wall_gap, wall.normal, H_block);

            SparseMatrix wall_hess;
            Barrier::compute_wall_hessian(vi, wall.normal, wall.offset, state,
                                          params.contact_gap_max, k_bar, wall_hess);

            for (int k = 0; k < wall_hess.outerSize(); ++k) {
                for (SparseMatrix::InnerIterator it(wall_hess, k); it; ++it) {
                    triplets.push_back(Triplet(it.row(), it.col(), it.value()));
                }
            }
        }
    }

    // Build sparse matrix from triplets
    hessian.setFromTriplets(triplets.begin(), triplets.end());
    
    // Make sure matrix is symmetric (average with transpose)
    SparseMatrix hessian_t = hessian.transpose();
    hessian = (hessian + hessian_t) * 0.5;
    
    // TODO: Add small regularization if needed for SPD enforcement
}

void Integrator::detect_collisions(const Mesh& mesh, const State& state,
                                  std::vector<ContactPair>& contacts) {
    contacts.clear();
    Collision::detect_all_collisions(mesh, state, contacts);
}

} // namespace ando_barrier
