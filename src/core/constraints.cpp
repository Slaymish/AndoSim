#include "constraints.h"

namespace ando_barrier {

void Constraints::add_pin(Index vertex_idx, const Vec3& target) {
    PinConstraint pin;
    pin.vertex_idx = vertex_idx;
    pin.target_position = target;
    pin.active = true;
    pins.push_back(pin);
}

void Constraints::add_wall(const Vec3& normal, Real offset, Real gap) {
    WallConstraint wall;
    wall.normal = normal.normalized();
    wall.offset = offset;
    wall.gap = gap;
    wall.active = true;
    walls.push_back(wall);
}

void Constraints::clear_contacts() {
    contacts.clear();
}

void Constraints::clear_strain_limits() {
    strain_limits.clear();
}

size_t Constraints::num_active_pins() const {
    size_t count = 0;
    for (const auto& pin : pins) {
        if (pin.active) ++count;
    }
    return count;
}

size_t Constraints::num_active_walls() const {
    size_t count = 0;
    for (const auto& wall : walls) {
        if (wall.active) ++count;
    }
    return count;
}

size_t Constraints::num_active_contacts() const {
    size_t count = 0;
    for (const auto& contact : contacts) {
        if (contact.active) ++count;
    }
    return count;
}

size_t Constraints::num_active_strain_limits() const {
    size_t count = 0;
    for (const auto& sl : strain_limits) {
        if (sl.active) ++count;
    }
    return count;
}

size_t Constraints::num_total_active() const {
    return num_active_pins() + num_active_walls() + 
           num_active_contacts() + num_active_strain_limits();
}

} // namespace ando_barrier
