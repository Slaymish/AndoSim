#pragma once

#include "types.h"
#include "mesh.h"
#include "state.h"
#include "collision.h"
#include <vector>

namespace ando_barrier {

// Collision validation metrics for quality assurance
struct CollisionMetrics {
    // Contact statistics
    int num_point_triangle = 0;
    int num_edge_edge = 0;
    int num_wall = 0;
    int num_total_contacts = 0;
    
    // Gap analysis
    Real min_gap = 0.0;              // Minimum gap (negative = penetration)
    Real max_gap = 0.0;              // Maximum gap
    Real avg_gap = 0.0;              // Average gap
    
    // Penetration detection
    int num_penetrations = 0;        // Contacts with gap < 0
    Real max_penetration = 0.0;      // Largest penetration depth (positive)
    Real avg_penetration = 0.0;      // Average penetration (of penetrating contacts)
    
    // CCD effectiveness
    bool ccd_enabled = false;
    int num_ccd_contacts = 0;        // Contacts found via CCD
    int num_broad_phase_contacts = 0; // Contacts found via broad phase
    Real ccd_effectiveness = 0.0;    // % contacts needing CCD
    
    // Velocity analysis
    Real max_relative_velocity = 0.0; // Highest contact approach speed
    Real avg_relative_velocity = 0.0; // Average approach speed
    
    // Quality indicators
    bool has_tunneling = false;      // Any penetration > 10% of gap_max
    bool has_major_penetration = false; // Any penetration > 1mm
    bool is_stable = true;           // All gaps within tolerance
    
    // Update from contact list
    void compute_from_contacts(const std::vector<ContactPair>& contacts,
                              Real gap_max,
                              bool ccd_enabled);
    
    // Get quality level (0=excellent, 1=good, 2=warning, 3=error)
    int quality_level() const;
    
    // Get quality description
    const char* quality_description() const;
};

// Collision validator for runtime checks
class CollisionValidator {
public:
    // Compute comprehensive collision metrics
    static CollisionMetrics compute_metrics(
        const Mesh& mesh,
        const State& state,
        const std::vector<ContactPair>& contacts,
        Real gap_max,
        bool ccd_enabled
    );
    
    // Check for penetrations in contact list
    static bool has_penetrations(const std::vector<ContactPair>& contacts);
    
    // Get maximum penetration depth
    static Real max_penetration_depth(const std::vector<ContactPair>& contacts);
    
    // Compute relative velocities at contacts
    static void compute_relative_velocities(
        const Mesh& mesh,
        const State& state,
        const std::vector<ContactPair>& contacts,
        std::vector<Real>& rel_velocities
    );
};

} // namespace ando_barrier
