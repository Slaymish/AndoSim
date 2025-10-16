#pragma once

#include "types.h"
#include "mesh.h"
#include "state.h"
#include "constraints.h"
#include "collision.h"
#include <vector>

namespace ando_barrier {

/**
 * Inexact Newton integrator with β accumulation (Algorithm 1)
 * 
 * Implements the paper's core time-stepping algorithm:
 * 1. β accumulation loop: while β < β_max, solve inner Newton step
 * 2. Line search for feasible α
 * 3. β ← β + (1-β)α
 * 4. Error reduction pass: one final Newton step with full β
 * 5. Velocity update: v = Δx / (βΔt)
 */
class Integrator {
public:
    /**
     * Take one simulation step
     * 
     * @param mesh Mesh topology
     * @param state Current state (positions, velocities, masses)
     * @param constraints Pin and wall constraints
     * @param params Simulation parameters
     */
    static void step(Mesh& mesh, State& state, Constraints& constraints, 
                    const SimParams& params);

private:
    /**
     * Inner Newton step: solve for search direction and take line search step
     * 
     * @param mesh Mesh topology
     * @param state Current state
     * @param x_target Target positions (x + βΔt v + βΔt² M⁻¹ f_ext)
     * @param contacts Current contact constraints
     * @param constraints Pin/wall constraints
     * @param params Simulation parameters
     * @param beta Current β value
     * @return Step length α taken (for β accumulation)
     */
    static Real inner_newton_step(
        const Mesh& mesh,
        State& state,
        const VecX& x_target,
        const std::vector<ContactPair>& contacts,
        const Constraints& constraints,
        const SimParams& params,
        Real beta
    );
    
    /**
     * Compute right-hand side: gradient of implicit Euler energy
     * 
     * E = (1/2Δt²) ||x - x̂||²_M + E_elastic + Σ V_barrier
     * ∇E = (1/Δt²) M(x - x̂) + ∇E_elastic + Σ ∇V_barrier
     * 
     * @param mesh Mesh topology
     * @param state Current state
     * @param x_target Target positions x̂
     * @param contacts Contact constraints
     * @param constraints Pin/wall constraints  
     * @param params Simulation parameters
     * @param beta Current β value (for barrier stiffness)
     * @param gradient Output gradient vector
     */
    static void compute_gradient(
        const Mesh& mesh,
        const State& state,
        const VecX& x_target,
        const std::vector<ContactPair>& contacts,
        const Constraints& constraints,
        const SimParams& params,
        Real beta,
        VecX& gradient
    );
    
    /**
     * Assemble system matrix (Hessian of implicit Euler energy)
     * 
     * H = (1/Δt²) M + H_elastic + Σ H_barrier
     * 
     * @param mesh Mesh topology
     * @param state Current state
     * @param contacts Contact constraints
     * @param constraints Pin/wall constraints
     * @param params Simulation parameters
     * @param beta Current β value
     * @param hessian Output sparse Hessian matrix
     */
    static void assemble_system_matrix(
        const Mesh& mesh,
        const State& state,
        const std::vector<ContactPair>& contacts,
        const Constraints& constraints,
        const SimParams& params,
        Real beta,
        SparseMatrix& hessian
    );
    
    /**
     * Detect all collisions and update contact constraints
     * 
     * @param mesh Mesh topology
     * @param state Current state
     * @param contacts Output contact pairs
     */
    static void detect_collisions(const Mesh& mesh, const State& state,
                                  std::vector<ContactPair>& contacts);
};

} // namespace ando_barrier
