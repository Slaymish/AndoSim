#pragma once

#include "types.h"
#include <vector>

namespace ando_barrier {

/**
 * Basic rigid body representation used for the hybrid rigid + elastic solver.
 *
 * The class stores the rest configuration of the rigid mesh (vertices in the
 * local body frame) together with mass and inertia properties.  During the
 * simulation the body is updated using semi-implicit Euler integration driven
 * by contact impulses that originate from the elastic solver.
 */
class RigidBody {
public:
    RigidBody();

    // Initialise from a triangle mesh and density.  Vertices are expressed in
    // world space and converted to the body frame (centred at the centroid).
    void initialize(const std::vector<Vec3>& vertices,
                    const std::vector<Triangle>& triangles,
                    Real density);

    // Accessors
    const std::vector<Vec3>& local_vertices() const { return m_vertices_local; }
    const std::vector<Triangle>& triangles() const { return m_triangles; }

    Real mass() const { return m_mass; }
    const Mat3& inertia_body() const { return m_inertia_body; }

    // Rigid transform state
    const Vec3& position() const { return m_position; }
    const Mat3& rotation() const { return m_rotation; }
    const Vec3& linear_velocity() const { return m_linear_velocity; }
    const Vec3& angular_velocity() const { return m_angular_velocity; }

    void set_position(const Vec3& p) { m_position = p; }
    void set_rotation(const Mat3& R) { m_rotation = R; }
    void set_linear_velocity(const Vec3& v) { m_linear_velocity = v; }
    void set_angular_velocity(const Vec3& w) { m_angular_velocity = w; }

    // Compute world-space vertex positions
    std::vector<Vec3> world_vertices() const;

    // Transform a world-space point into the local body frame
    Vec3 to_local(const Vec3& world_point) const;

    // Velocity at a world-space point due to rigid body motion
    Vec3 velocity_at_point(const Vec3& world_point) const;

    // Apply an impulse (change in momentum) at a world-space point
    void apply_impulse(const Vec3& world_point, const Vec3& impulse);

    // Apply a force/torque pair for a duration dt (used for semi-implicit
    // integration driven by barrier forces).
    void apply_force(const Vec3& world_point, const Vec3& force, Real dt);

    // Advance the rigid body state using semi-implicit Euler integration.
    void integrate(Real dt);

    // Reset accumulated forces/torques.  Integration automatically clears
    // them, but exposing a manual reset is convenient for tests.
    void clear_accumulators();

    Mat3 inertia_world_inv() const;

private:
    void compute_mass_properties(Real density);

    std::vector<Vec3> m_vertices_local;
    std::vector<Triangle> m_triangles;

    Real m_mass;
    Mat3 m_inertia_body;
    Mat3 m_inertia_body_inv;

    Vec3 m_position;
    Mat3 m_rotation;
    Vec3 m_linear_velocity;
    Vec3 m_angular_velocity;

    Vec3 m_accumulated_force;
    Vec3 m_accumulated_torque;
};

} // namespace ando_barrier

