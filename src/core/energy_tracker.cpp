#include "energy_tracker.h"
#include "elasticity.h"
#include "barrier.h"

namespace ando_barrier {

Real EnergyTracker::compute_kinetic_energy(const State& state) {
    Real ke = 0.0;
    for (size_t i = 0; i < state.num_vertices(); ++i) {
        Real mass = state.masses[i];
        Real v_squared = state.velocities[i].squaredNorm();
        ke += 0.5 * mass * v_squared;
    }
    return ke;
}

Vec3 EnergyTracker::compute_linear_momentum(const State& state) {
    Vec3 momentum = Vec3::Zero();
    for (size_t i = 0; i < state.num_vertices(); ++i) {
        momentum += state.masses[i] * state.velocities[i];
    }
    return momentum;
}

Vec3 EnergyTracker::compute_angular_momentum(const State& state) {
    Vec3 angular = Vec3::Zero();
    for (size_t i = 0; i < state.num_vertices(); ++i) {
        Vec3 r = state.positions[i];
        Vec3 p = state.masses[i] * state.velocities[i];
        angular += r.cross(p);
    }
    return angular;
}

Real EnergyTracker::compute_max_velocity(const State& state) {
    Real max_v = 0.0;
    for (size_t i = 0; i < state.num_vertices(); ++i) {
        Real v = state.velocities[i].norm();
        max_v = std::max(max_v, v);
    }
    return max_v;
}

EnergyDiagnostics EnergyTracker::compute(
    const Mesh& mesh,
    const State& state,
    const Constraints& constraints,
    const SimParams& params
) {
    EnergyDiagnostics diag;
    
    // Kinetic energy
    diag.kinetic_energy = compute_kinetic_energy(state);
    
    // Elastic energy
    diag.elastic_energy = Elasticity::compute_energy(mesh, state);
    
    // Barrier energy not currently tracked (typically small compared to elastic/kinetic)
    diag.barrier_energy = 0.0;
    
    // Total energy
    diag.total_energy = diag.kinetic_energy + diag.elastic_energy + diag.barrier_energy;
    
    // Momentum
    diag.linear_momentum = compute_linear_momentum(state);
    diag.angular_momentum = compute_angular_momentum(state);
    
    // Velocity stats
    diag.max_velocity = compute_max_velocity(state);
    
    // Constraint counts
    diag.num_contacts = static_cast<int>(constraints.num_active_contacts());
    diag.num_pins = static_cast<int>(constraints.num_active_pins());
    
    return diag;
}

void EnergyDiagnostics::update_drift(Real prev_total_energy) {
    if (prev_total_energy > 1e-12) {  // Avoid division by near-zero
        energy_drift_absolute = total_energy - prev_total_energy;
        energy_drift_percent = (energy_drift_absolute / prev_total_energy) * 100.0;
    } else {
        energy_drift_absolute = 0.0;
        energy_drift_percent = 0.0;
    }
}

} // namespace ando_barrier
