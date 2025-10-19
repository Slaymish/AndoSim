#pragma once

#include "types.h"
#include "mesh.h"
#include "state.h"
#include "constraints.h"

namespace ando_barrier {

// Energy diagnostics for validation and visualization
struct EnergyDiagnostics {
    Real kinetic_energy = 0.0;           // (1/2) m v²
    Real elastic_energy = 0.0;           // Stretching/bending
    Real barrier_energy = 0.0;           // Contact barriers
    Real total_energy = 0.0;             // Sum of all
    
    Vec3 linear_momentum = Vec3::Zero(); // Σ m v
    Vec3 angular_momentum = Vec3::Zero(); // Σ r × (m v)
    
    Real max_velocity = 0.0;             // Max vertex speed
    Real max_acceleration = 0.0;         // Max vertex accel (if prev velocities available)
    
    int num_contacts = 0;                // Active contacts
    int num_pins = 0;                    // Active pins
    
    // Add to previous energy for drift tracking
    void update_drift(Real prev_total_energy);
    Real energy_drift_percent = 0.0;     // Percentage drift from initial
    Real energy_drift_absolute = 0.0;    // Absolute drift
};

// Compute comprehensive energy diagnostics
class EnergyTracker {
public:
    EnergyTracker() = default;
    
    // Compute all energy terms and diagnostics
    static EnergyDiagnostics compute(
        const Mesh& mesh,
        const State& state,
        const Constraints& constraints,
        const SimParams& params
    );
    
    // Compute kinetic energy: (1/2) Σ m_i ||v_i||²
    static Real compute_kinetic_energy(const State& state);
    
    // Compute linear momentum: Σ m_i v_i
    static Vec3 compute_linear_momentum(const State& state);
    
    // Compute angular momentum: Σ r_i × (m_i v_i)
    static Vec3 compute_angular_momentum(const State& state);
    
    // Find maximum velocity magnitude
    static Real compute_max_velocity(const State& state);
};

} // namespace ando_barrier
