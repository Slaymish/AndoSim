#pragma once

#include "types.h"
#include "mesh.h"
#include "state.h"

namespace ando_barrier {

/**
 * Adaptive timestepping based on CFL (Courant-Friedrichs-Lewy) condition
 * 
 * Dynamically adjusts timestep based on:
 * - Maximum velocity in the system
 * - Minimum edge length in the mesh
 * - Safety factor for stability
 * 
 * Increases dt when velocities are low (cloth settling)
 * Decreases dt when velocities spike (collisions)
 * 
 * Reference: Phase 4 Task 3 specification
 */
class AdaptiveTimestep {
public:
    /**
     * Compute next timestep using CFL condition
     * 
     * @param velocities Current velocities (size 3*num_vertices)
     * @param mesh Mesh topology (for edge lengths)
     * @param current_dt Current timestep in seconds
     * @param dt_min Minimum allowed timestep (stability floor)
     * @param dt_max Maximum allowed timestep (user preference)
     * @param safety_factor CFL safety factor (typically 0.5)
     * @return Next timestep in seconds, clamped to [dt_min, dt_max]
     * 
     * CFL condition: dt = safety_factor * min_edge_length / max_velocity
     * 
     * Special cases:
     * - If max_velocity ≈ 0: Return dt_max (static/settled state)
     * - If dt would increase: Smooth transition (max 1.5× per step)
     * - If dt would decrease: Immediate change (safety critical)
     */
    static Real compute_next_dt(
        const VecX& velocities,
        const Mesh& mesh,
        Real current_dt,
        Real dt_min,
        Real dt_max,
        Real safety_factor = static_cast<Real>(0.5)
    );
    
    /**
     * Compute CFL timestep from velocity and mesh resolution
     * 
     * @param max_velocity Maximum velocity magnitude in m/s
     * @param min_edge_length Smallest edge in mesh (meters)
     * @param safety_factor CFL safety factor
     * @return CFL timestep in seconds
     * 
     * Formula: dt_cfl = safety_factor * (min_edge / max_velocity)
     * 
     * Physical interpretation: Timestep such that fastest-moving vertex
     * travels at most (safety_factor * min_edge) distance per step.
     */
    static Real compute_cfl_timestep(
        Real max_velocity,
        Real min_edge_length,
        Real safety_factor
    );
    
    /**
     * Smooth timestep changes to avoid oscillations
     * 
     * @param current_dt Current timestep
     * @param target_dt Desired timestep from CFL
     * @param max_increase_ratio Maximum ratio for increasing dt (e.g., 1.5)
     * @return Smoothed timestep
     * 
     * Rules:
     * - Increases: Limited to max_increase_ratio × current_dt per step
     * - Decreases: Immediate (safety critical, no smoothing)
     * 
     * Prevents aggressive dt growth that could cause instability.
     */
    static Real smooth_dt_change(
        Real current_dt,
        Real target_dt,
        Real max_increase_ratio = static_cast<Real>(1.5)
    );
    
    /**
     * Compute minimum edge length in mesh
     * 
     * @param mesh Mesh topology and positions
     * @return Length of shortest edge in meters
     * 
     * Used as spatial resolution for CFL condition.
     * Cached at initialization if mesh topology is static.
     */
    static Real compute_min_edge_length(const Mesh& mesh);
    
    /**
     * Compute maximum velocity magnitude
     * 
     * @param velocities Velocity vector (size 3*num_vertices)
     * @return Maximum velocity magnitude in m/s
     * 
     * Computed each frame for CFL condition.
     * Returns 0 if all velocities are below threshold (1e-6 m/s).
     */
    static Real compute_max_velocity(const VecX& velocities);
    
private:
    // Velocity threshold for "static" detection (m/s)
    static constexpr Real kStaticVelocityThreshold = static_cast<Real>(1e-6);
    
    // Minimum edge length threshold (meters)
    static constexpr Real kMinEdgeLengthThreshold = static_cast<Real>(1e-5);
};

} // namespace ando_barrier
