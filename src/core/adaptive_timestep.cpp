#include "adaptive_timestep.h"
#include <algorithm>
#include <cmath>
#include <limits>

namespace ando_barrier {

Real AdaptiveTimestep::compute_next_dt(
    const VecX& velocities,
    const Mesh& mesh,
    Real current_dt,
    Real dt_min,
    Real dt_max,
    Real safety_factor
) {
    // Compute maximum velocity
    Real max_vel = compute_max_velocity(velocities);
    
    // Special case: Static or nearly static (settled cloth)
    if (max_vel < kStaticVelocityThreshold) {
        // No motion → use maximum timestep
        return dt_max;
    }
    
    // Compute minimum edge length (spatial resolution)
    Real min_edge = compute_min_edge_length(mesh);
    
    // Guard against degenerate meshes
    if (min_edge < kMinEdgeLengthThreshold) {
        min_edge = kMinEdgeLengthThreshold;
    }
    
    // Compute CFL timestep
    Real dt_cfl = compute_cfl_timestep(max_vel, min_edge, safety_factor);
    
    // Clamp to user-specified bounds
    Real dt_target = std::clamp(dt_cfl, dt_min, dt_max);
    
    // Smooth timestep changes (limit growth rate, allow immediate shrinkage)
    Real dt_next = smooth_dt_change(current_dt, dt_target);
    
    // Final clamp (in case smoothing violated bounds)
    return std::clamp(dt_next, dt_min, dt_max);
}

Real AdaptiveTimestep::compute_cfl_timestep(
    Real max_velocity,
    Real min_edge_length,
    Real safety_factor
) {
    // CFL condition: dt = safety * (dx / v_max)
    // Interpretation: Fastest vertex travels (safety * dx) per step
    
    if (max_velocity < kStaticVelocityThreshold) {
        // Avoid division by near-zero
        return static_cast<Real>(1.0);  // Large timestep (will be clamped to dt_max)
    }
    
    Real dt_cfl = safety_factor * min_edge_length / max_velocity;
    
    return dt_cfl;
}

Real AdaptiveTimestep::smooth_dt_change(
    Real current_dt,
    Real target_dt,
    Real max_increase_ratio
) {
    if (target_dt < current_dt) {
        // Decrease: Immediate (safety critical)
        // Velocity spike → reduce dt now to maintain stability
        return target_dt;
    }
    
    // Increase: Smooth growth (prevent oscillations)
    // Limit growth to max_increase_ratio × current_dt
    Real max_allowed_dt = current_dt * max_increase_ratio;
    
    return std::min(target_dt, max_allowed_dt);
}

Real AdaptiveTimestep::compute_min_edge_length(const Mesh& mesh) {
    if (mesh.edges.empty()) {
        return static_cast<Real>(0.0);
    }

    Real min_edge_sq = std::numeric_limits<Real>::max();
    bool found_valid_edge = false;

    const size_t num_vertices = mesh.vertices.size();

    // Iterate over all edges
    for (const auto& edge : mesh.edges) {
        const Index v0 = edge.v[0];
        const Index v1 = edge.v[1];

        // Skip edges that reference invalid vertices
        if (v0 < 0 || v1 < 0 ||
            static_cast<size_t>(v0) >= num_vertices ||
            static_cast<size_t>(v1) >= num_vertices) {
            continue;
        }

        // Get vertex positions
        const Vec3& p0 = mesh.vertices[v0];
        const Vec3& p1 = mesh.vertices[v1];

        // Compute squared edge length
        const Real edge_length_sq = (p1 - p0).squaredNorm();

        if (!std::isfinite(edge_length_sq)) {
            continue;
        }

        min_edge_sq = std::min(min_edge_sq, edge_length_sq);
        found_valid_edge = true;
    }

    if (!found_valid_edge) {
        return static_cast<Real>(0.0);
    }

    const Real min_edge = std::sqrt(std::max(min_edge_sq, static_cast<Real>(0.0)));

    if (!std::isfinite(min_edge)) {
        return static_cast<Real>(0.0);
    }

    return min_edge;
}

Real AdaptiveTimestep::compute_max_velocity(const VecX& velocities) {
    Real max_vel_sq = static_cast<Real>(0.0);
    
    const int num_vertices = velocities.size() / 3;
    
    for (int i = 0; i < num_vertices; ++i) {
        Vec3 v(
            velocities[3 * i + 0],
            velocities[3 * i + 1],
            velocities[3 * i + 2]
        );
        
        Real vel_mag_sq = v.squaredNorm();
        max_vel_sq = std::max(max_vel_sq, vel_mag_sq);
    }
    
    return std::sqrt(max_vel_sq);
}

} // namespace ando_barrier
