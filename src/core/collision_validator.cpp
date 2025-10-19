#include "collision_validator.h"
#include <algorithm>
#include <cmath>

namespace ando_barrier {

void CollisionMetrics::compute_from_contacts(
    const std::vector<ContactPair>& contacts,
    Real gap_max,
    bool ccd_enabled_param
) {
    ccd_enabled = ccd_enabled_param;
    num_total_contacts = static_cast<int>(contacts.size());
    
    if (contacts.empty()) {
        // No contacts - all metrics are zero/default
        min_gap = 0.0;
        max_gap = 0.0;
        avg_gap = 0.0;
        num_penetrations = 0;
        max_penetration = 0.0;
        avg_penetration = 0.0;
        max_relative_velocity = 0.0;
        avg_relative_velocity = 0.0;
        has_tunneling = false;
        has_major_penetration = false;
        is_stable = true;
        return;
    }
    
    // Initialize extremes
    min_gap = contacts[0].gap;
    max_gap = contacts[0].gap;
    Real sum_gap = 0.0;
    Real sum_penetration = 0.0;
    
    // Count by type
    num_point_triangle = 0;
    num_edge_edge = 0;
    num_wall = 0;
    
    // Analyze contacts
    for (const auto& contact : contacts) {
        // Type counting
        switch (contact.type) {
            case ContactType::POINT_TRIANGLE:
                num_point_triangle++;
                break;
            case ContactType::EDGE_EDGE:
                num_edge_edge++;
                break;
            case ContactType::WALL:
                num_wall++;
                break;
        }
        
        // Gap statistics
        Real gap = contact.gap;
        min_gap = std::min(min_gap, gap);
        max_gap = std::max(max_gap, gap);
        sum_gap += gap;
        
        // Penetration detection (gap < 0)
        if (gap < 0.0) {
            num_penetrations++;
            Real penetration = -gap; // Make positive
            max_penetration = std::max(max_penetration, penetration);
            sum_penetration += penetration;
            
            // Major penetration check (> 1mm)
            if (penetration > 0.001) {
                has_major_penetration = true;
            }
            
            // Tunneling check (> 10% of gap_max)
            if (penetration > 0.1 * gap_max) {
                has_tunneling = true;
            }
        }
    }
    
    // Compute averages
    avg_gap = sum_gap / num_total_contacts;
    
    if (num_penetrations > 0) {
        avg_penetration = sum_penetration / num_penetrations;
        is_stable = false; // Any penetration means unstable
    } else {
        avg_penetration = 0.0;
        is_stable = true;
    }
    
    // CCD effectiveness (simplified - assume CCD needed for close contacts)
    // In practice, this would track which contacts were found via CCD sweep
    // vs broad phase. For now, estimate based on gap proximity to limit.
    num_ccd_contacts = 0;
    num_broad_phase_contacts = 0;
    
    for (const auto& contact : contacts) {
        if (ccd_enabled && contact.gap < gap_max * 0.5) {
            num_ccd_contacts++; // Close contacts likely need CCD
        } else {
            num_broad_phase_contacts++;
        }
    }
    
    if (ccd_enabled && num_total_contacts > 0) {
        ccd_effectiveness = (Real)num_ccd_contacts / (Real)num_total_contacts * 100.0;
    } else {
        ccd_effectiveness = 0.0;
    }
}

int CollisionMetrics::quality_level() const {
    if (has_tunneling) return 3;           // ERROR: tunneling detected
    if (has_major_penetration) return 3;   // ERROR: major penetration
    if (max_penetration > 0.0001) return 2; // WARNING: minor penetration (>0.1mm)
    if (num_penetrations > 0) return 1;    // GOOD: tiny penetrations (<0.1mm)
    return 0;                               // EXCELLENT: no penetrations
}

const char* CollisionMetrics::quality_description() const {
    int level = quality_level();
    switch (level) {
        case 0: return "Excellent - No penetrations";
        case 1: return "Good - Tiny penetrations (<0.1mm)";
        case 2: return "Warning - Minor penetrations detected";
        case 3: return "Error - Major penetrations or tunneling";
        default: return "Unknown";
    }
}

CollisionMetrics CollisionValidator::compute_metrics(
    const Mesh& mesh,
    const State& state,
    const std::vector<ContactPair>& contacts,
    Real gap_max,
    bool ccd_enabled
) {
    CollisionMetrics metrics;
    metrics.compute_from_contacts(contacts, gap_max, ccd_enabled);
    
    // Compute relative velocities if state has velocities
    std::vector<Real> rel_velocities;
    compute_relative_velocities(mesh, state, contacts, rel_velocities);
    
    if (!rel_velocities.empty()) {
        metrics.max_relative_velocity = *std::max_element(rel_velocities.begin(), rel_velocities.end());
        
        Real sum_vel = 0.0;
        for (Real v : rel_velocities) {
            sum_vel += v;
        }
        metrics.avg_relative_velocity = sum_vel / rel_velocities.size();
    }
    
    return metrics;
}

bool CollisionValidator::has_penetrations(const std::vector<ContactPair>& contacts) {
    for (const auto& contact : contacts) {
        if (contact.gap < 0.0) {
            return true;
        }
    }
    return false;
}

Real CollisionValidator::max_penetration_depth(const std::vector<ContactPair>& contacts) {
    Real max_pen = 0.0;
    for (const auto& contact : contacts) {
        if (contact.gap < 0.0) {
            max_pen = std::max(max_pen, -contact.gap);
        }
    }
    return max_pen;
}

void CollisionValidator::compute_relative_velocities(
    const Mesh& mesh,
    const State& state,
    const std::vector<ContactPair>& contacts,
    std::vector<Real>& rel_velocities
) {
    rel_velocities.clear();
    rel_velocities.reserve(contacts.size());
    
    for (const auto& contact : contacts) {
        if (contact.type == ContactType::POINT_TRIANGLE) {
            // Point-triangle: velocity of point toward triangle
            Vec3 v_point = state.velocities[contact.idx0];
            
            // Triangle average velocity
            Vec3 v_tri = (state.velocities[contact.idx1] +
                         state.velocities[contact.idx2] +
                         state.velocities[contact.idx3]) / 3.0;
            
            // Relative velocity along normal
            Vec3 v_rel = v_point - v_tri;
            Real v_normal = v_rel.dot(contact.normal);
            rel_velocities.push_back(std::abs(v_normal));
            
        } else if (contact.type == ContactType::EDGE_EDGE) {
            // Edge-edge: average velocities
            Vec3 v_edge0 = (state.velocities[contact.idx0] + state.velocities[contact.idx1]) / 2.0;
            Vec3 v_edge1 = (state.velocities[contact.idx2] + state.velocities[contact.idx3]) / 2.0;
            
            Vec3 v_rel = v_edge0 - v_edge1;
            Real v_normal = v_rel.dot(contact.normal);
            rel_velocities.push_back(std::abs(v_normal));
            
        } else if (contact.type == ContactType::WALL) {
            // Wall: just point velocity along normal
            Vec3 v_point = state.velocities[contact.idx0];
            Real v_normal = v_point.dot(contact.normal);
            rel_velocities.push_back(std::abs(v_normal));
        }
    }
}

} // namespace ando_barrier
