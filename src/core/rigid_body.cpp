#include "rigid_body.h"

#include <Eigen/Geometry>
#include <algorithm>
#include <limits>

namespace ando_barrier {

RigidBody::RigidBody()
    : m_mass(1.0),
      m_inertia_body(Mat3::Identity()),
      m_inertia_body_inv(Mat3::Identity()),
      m_position(Vec3::Zero()),
      m_rotation(Mat3::Identity()),
      m_linear_velocity(Vec3::Zero()),
      m_angular_velocity(Vec3::Zero()),
      m_accumulated_force(Vec3::Zero()),
      m_accumulated_torque(Vec3::Zero()) {}

void RigidBody::initialize(const std::vector<Vec3>& vertices,
                           const std::vector<Triangle>& triangles,
                           Real density) {
    m_triangles = triangles;

    if (vertices.empty()) {
        m_vertices_local.clear();
        m_mass = 0.0;
        m_inertia_body.setZero();
        m_inertia_body_inv.setZero();
        return;
    }

    // Compute centroid to establish local frame
    Vec3 centroid = Vec3::Zero();
    for (const Vec3& v : vertices) {
        centroid += v;
    }
    centroid /= static_cast<Real>(vertices.size());

    m_vertices_local.resize(vertices.size());
    for (size_t i = 0; i < vertices.size(); ++i) {
        m_vertices_local[i] = vertices[i] - centroid;
    }

    m_position = centroid;
    m_rotation = Mat3::Identity();
    m_linear_velocity.setZero();
    m_angular_velocity.setZero();

    compute_mass_properties(density);
    clear_accumulators();
}

void RigidBody::compute_mass_properties(Real density) {
    // Approximate mass using bounding box volume; fall back to unit mass if the
    // bounding box is degenerate.
    Vec3 min_corner = Vec3::Constant(std::numeric_limits<Real>::max());
    Vec3 max_corner = Vec3::Constant(-std::numeric_limits<Real>::max());

    for (const Vec3& v : m_vertices_local) {
        Vec3 world = v + m_position;  // local positions relative to centroid
        min_corner = min_corner.cwiseMin(world);
        max_corner = max_corner.cwiseMax(world);
    }

    Vec3 extents = max_corner - min_corner;
    Real volume = std::max(extents[0], Real(1e-6)) *
                  std::max(extents[1], Real(1e-6)) *
                  std::max(extents[2], Real(1e-6));

    m_mass = std::max(density * volume, Real(1e-3));

    // Box inertia tensor about centre of mass
    Real x2 = extents[0] * extents[0];
    Real y2 = extents[1] * extents[1];
    Real z2 = extents[2] * extents[2];

    m_inertia_body = Mat3::Zero();
    m_inertia_body(0, 0) = (m_mass / Real(12.0)) * (y2 + z2);
    m_inertia_body(1, 1) = (m_mass / Real(12.0)) * (x2 + z2);
    m_inertia_body(2, 2) = (m_mass / Real(12.0)) * (x2 + y2);

    // Avoid degeneracy
    for (int i = 0; i < 3; ++i) {
        if (m_inertia_body(i, i) < Real(1e-6)) {
            m_inertia_body(i, i) = Real(1e-6);
        }
    }

    m_inertia_body_inv = m_inertia_body.inverse();
}

std::vector<Vec3> RigidBody::world_vertices() const {
    std::vector<Vec3> out;
    out.reserve(m_vertices_local.size());
    for (const Vec3& v : m_vertices_local) {
        out.push_back(m_position + m_rotation * v);
    }
    return out;
}

Vec3 RigidBody::to_local(const Vec3& world_point) const {
    return m_rotation.transpose() * (world_point - m_position);
}

Vec3 RigidBody::velocity_at_point(const Vec3& world_point) const {
    Vec3 r = world_point - m_position;
    return m_linear_velocity + m_angular_velocity.cross(r);
}

Mat3 RigidBody::inertia_world_inv() const {
    Mat3 R = m_rotation;
    return R * m_inertia_body_inv * R.transpose();
}

void RigidBody::apply_impulse(const Vec3& world_point, const Vec3& impulse) {
    if (m_mass <= Real(0)) {
        return;
    }

    Vec3 delta_v = impulse / m_mass;
    m_linear_velocity += delta_v;

    Vec3 r = world_point - m_position;
    Vec3 delta_w = inertia_world_inv() * (r.cross(impulse));
    m_angular_velocity += delta_w;
}

void RigidBody::apply_force(const Vec3& world_point, const Vec3& force, Real dt) {
    if (m_mass <= Real(0)) {
        return;
    }

    m_accumulated_force += force;
    Vec3 r = world_point - m_position;
    m_accumulated_torque += r.cross(force);

    // Integrate immediately if dt > 0
    if (dt > Real(0)) {
        Vec3 impulse = force * dt;
        Vec3 torque_impulse = m_accumulated_torque * dt;

        m_linear_velocity += impulse / m_mass;
        m_angular_velocity += inertia_world_inv() * torque_impulse;

        m_accumulated_force.setZero();
        m_accumulated_torque.setZero();
    }
}

void RigidBody::integrate(Real dt) {
    if (m_mass <= Real(0)) {
        return;
    }

    // Semi-implicit Euler
    Vec3 acceleration = m_accumulated_force / m_mass;
    m_linear_velocity += acceleration * dt;

    Mat3 I_inv_world = inertia_world_inv();
    Vec3 angular_acc = I_inv_world * m_accumulated_torque;
    m_angular_velocity += angular_acc * dt;

    m_position += m_linear_velocity * dt;

    Real omega_norm = m_angular_velocity.norm();
    if (omega_norm > Real(1e-8)) {
        Real theta = omega_norm * dt;
        Vec3 axis = m_angular_velocity / omega_norm;
        Eigen::AngleAxis<Real> aa(theta, axis);
        Mat3 delta_R = aa.toRotationMatrix();
        m_rotation = delta_R * m_rotation;
    }

    clear_accumulators();
}

void RigidBody::clear_accumulators() {
    m_accumulated_force.setZero();
    m_accumulated_torque.setZero();
}

} // namespace ando_barrier

