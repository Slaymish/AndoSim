#pragma once

#include "types.h"
#include "mesh.h"
#include <vector>

namespace ando_barrier {

// Physics state for simulation
class State {
public:
    // Dynamic state
    std::vector<Vec3> positions;    // x (N×3)
    std::vector<Vec3> velocities;   // v (N×3)
    std::vector<Real> masses;       // m (N) - lumped masses per vertex
    
    // Previous step positions (for friction/velocity update)
    std::vector<Vec3> positions_prev;
    
    State() = default;
    
    // Initialize from mesh
    void initialize(const Mesh& mesh);
    
    // Compute lumped masses from mesh (area × thickness × ρ distributed to vertices)
    void compute_lumped_masses(const Mesh& mesh);
    
    // Update from integration step
    void update_positions(const std::vector<Vec3>& new_positions);
    void update_velocities(Real beta_dt); // Δx / (βΔt)
    
    // Access
    size_t num_vertices() const { return positions.size(); }
    
    // Flatten to single vector for solver
    void flatten_positions(VecX& x) const;
    void unflatten_positions(const VecX& x);
};

} // namespace ando_barrier
