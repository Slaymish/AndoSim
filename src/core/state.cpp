#include "state.h"

#include <stdexcept>

namespace ando_barrier {

void State::initialize(const Mesh& mesh) {
    if (mesh.num_vertices() == 0) {
        throw std::invalid_argument("Mesh must be initialised before creating a state");
    }

    positions = mesh.vertices;
    positions_prev = mesh.vertices;
    velocities.resize(mesh.num_vertices(), Vec3::Zero());
    
    compute_lumped_masses(mesh);
}

void State::compute_lumped_masses(const Mesh& mesh) {
    masses.clear();
    masses.resize(mesh.num_vertices(), 0.0);
    
    // Distribute face mass equally to three vertices
    for (size_t i = 0; i < mesh.num_triangles(); ++i) {
        const Triangle& tri = mesh.triangles[i];
        Real face_mass = mesh.rest_areas[i] * mesh.material.thickness * mesh.material.density;
        Real vertex_mass = face_mass / 3.0;
        
        masses[tri.v[0]] += vertex_mass;
        masses[tri.v[1]] += vertex_mass;
        masses[tri.v[2]] += vertex_mass;
    }
}

void State::update_positions(const std::vector<Vec3>& new_positions) {
    positions_prev = positions;
    positions = new_positions;
}

void State::update_velocities(Real beta_dt) {
    // v = Δx / (βΔt)
    for (size_t i = 0; i < positions.size(); ++i) {
        velocities[i] = (positions[i] - positions_prev[i]) / beta_dt;
    }
}

void State::flatten_positions(VecX& x) const {
    x.resize(positions.size() * 3);
    for (size_t i = 0; i < positions.size(); ++i) {
        x[i * 3 + 0] = positions[i][0];
        x[i * 3 + 1] = positions[i][1];
        x[i * 3 + 2] = positions[i][2];
    }
}

void State::unflatten_positions(const VecX& x) {
    for (size_t i = 0; i < positions.size(); ++i) {
        positions[i][0] = x[i * 3 + 0];
        positions[i][1] = x[i * 3 + 1];
        positions[i][2] = x[i * 3 + 2];
    }
}

} // namespace ando_barrier
