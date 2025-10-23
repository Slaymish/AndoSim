#pragma once

#include "types.h"
#include <vector>

namespace ando_barrier {

// Pin constraint: fix vertex to target position
struct PinConstraint {
    Index vertex_idx;
    Vec3 target_position;
    bool active = true;
};

// Alias for convenience
using Pin = PinConstraint;

// Wall constraint: plane defined by normal and offset
struct WallConstraint {
    Vec3 normal;      // Plane normal (normalized)
    Real offset;      // Distance from origin
    Real gap;         // g_wall
    bool active = true;
};

// Contact constraint (computed per step)
struct ContactConstraint {
    Index vertex_idx;           // Point vertex
    Index triangle_idx;         // Triangle face (or -1 for edge-edge)
    Vec3 witness_point;         // q (point on triangle/edge)
    Vec3 normal;                // Contact normal (fixed during step)
    Real gap;                   // Current gap g
    Real stiffness;             // k̄ for this constraint
    bool active = true;
};

// Strain limiting constraint (per-face)
struct StrainConstraint {
    Index face_idx;
    Real sigma;                 // Singular value associated with constraint
    int singular_index = 0;     // 0 or 1 (σ1 or σ2)
    Real stiffness;             // k_SL
    bool active = true;
};

// Container for all constraints
class Constraints {
public:
    std::vector<PinConstraint> pins;
    std::vector<WallConstraint> walls;
    std::vector<ContactConstraint> contacts;  // Dynamic, rebuilt each step
    std::vector<StrainConstraint> strain_limits; // Dynamic, rebuilt each step
    
    Constraints() = default;
    
    // Add constraints
    void add_pin(Index vertex_idx, const Vec3& target);
    void add_wall(const Vec3& normal, Real offset, Real gap);
    
    // Clear dynamic constraints (contacts, strain limits)
    void clear_contacts();
    void clear_strain_limits();
    
    // Count active constraints
    size_t num_active_pins() const;
    size_t num_active_walls() const;
    size_t num_active_contacts() const;
    size_t num_active_strain_limits() const;
    size_t num_total_active() const;
};

} // namespace ando_barrier
