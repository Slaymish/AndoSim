#include "../src/core/collision_validator.h"
#include "../src/core/mesh.h"
#include "../src/core/state.h"
#include <cassert>
#include <iostream>
#include <vector>

using namespace ando_barrier;

namespace {

void initialize_simple_mesh(Mesh& mesh, State& state) {
    std::vector<Vec3> vertices = {
        Vec3(0.0, 0.0, 0.0),
        Vec3(1.0, 0.0, 0.0),
        Vec3(0.0, 0.0, 1.0),
        Vec3(1.0, 0.0, 1.0)
    };

    std::vector<Triangle> triangles = {
        Triangle(0, 1, 2),
        Triangle(1, 3, 2)
    };

    Material material;
    mesh.initialize(vertices, triangles, material);
    state.initialize(mesh);
}

void test_empty_contact_metrics() {
    std::cout << "Testing collision metrics with no contacts..." << std::endl;

    Mesh mesh;
    State state;
    initialize_simple_mesh(mesh, state);

    std::vector<ContactPair> contacts;
    CollisionMetrics metrics = CollisionValidator::compute_metrics(
        mesh, state, contacts, /*gap_max=*/0.002f, /*ccd_enabled=*/true);

    assert(metrics.num_total_contacts == 0);
    assert(metrics.num_penetrations == 0);
    assert(metrics.is_stable);
    assert(metrics.ccd_effectiveness == 0.0f);
    assert(metrics.quality_level() == 0);

    std::cout << "  ✓ Empty contact metrics passed" << std::endl;
}

void test_populated_contact_metrics() {
    std::cout << "Testing collision metrics with mixed contacts..." << std::endl;

    Mesh mesh;
    State state;
    initialize_simple_mesh(mesh, state);

    // Assign distinct velocities to exercise relative velocity computation.
    state.velocities[0] = Vec3(0.0, -1.0, 0.0);
    state.velocities[1] = Vec3(0.0, 0.25, 0.0);
    state.velocities[2] = Vec3(0.0, -0.4, 0.0);
    state.velocities[3] = Vec3(0.0, 0.1, 0.0);

    std::vector<ContactPair> contacts;

    // Point-triangle contact with mild penetration.
    ContactPair pt;
    pt.type = ContactType::POINT_TRIANGLE;
    pt.idx0 = 0;
    pt.idx1 = 1;
    pt.idx2 = 2;
    pt.idx3 = 3;
    pt.gap = -5.0e-4f;
    pt.normal = Vec3(0.0, 1.0, 0.0);
    contacts.push_back(pt);

    // Edge-edge contact that is close but not penetrating.
    ContactPair ee;
    ee.type = ContactType::EDGE_EDGE;
    ee.idx0 = 0;
    ee.idx1 = 1;
    ee.idx2 = 2;
    ee.idx3 = 3;
    ee.gap = 2.0e-4f;
    ee.normal = Vec3(0.0, 1.0, 0.0);
    contacts.push_back(ee);

    // Wall contact with a major penetration to trigger warnings.
    ContactPair wall;
    wall.type = ContactType::WALL;
    wall.idx0 = 2;
    wall.gap = -1.5e-3f;
    wall.normal = Vec3(0.0, 1.0, 0.0);
    contacts.push_back(wall);

    const Real gap_max = 0.002f;
    CollisionMetrics metrics = CollisionValidator::compute_metrics(
        mesh, state, contacts, gap_max, /*ccd_enabled=*/true);

    assert(metrics.num_total_contacts == 3);
    assert(metrics.num_point_triangle == 1);
    assert(metrics.num_edge_edge == 1);
    assert(metrics.num_wall == 1);

    assert(metrics.num_penetrations == 2);
    assert(std::abs(metrics.max_penetration - 1.5e-3f) < 1e-6f);
    assert(metrics.has_major_penetration);
    assert(metrics.has_tunneling);

    assert(metrics.ccd_enabled);
    assert(metrics.num_ccd_contacts == 3);
    assert(metrics.ccd_effectiveness > 99.0f);

    assert(metrics.max_relative_velocity > 0.5f);
    assert(metrics.avg_relative_velocity > 0.0f);

    assert(metrics.quality_level() == 3);
    assert(CollisionValidator::has_penetrations(contacts));
    assert(std::abs(CollisionValidator::max_penetration_depth(contacts) - 1.5e-3f) < 1e-6f);

    // CCD disabled should zero-out CCD metrics while keeping penetration stats.
    CollisionMetrics metrics_no_ccd = CollisionValidator::compute_metrics(
        mesh, state, contacts, gap_max, /*ccd_enabled=*/false);
    assert(!metrics_no_ccd.ccd_enabled);
    assert(metrics_no_ccd.ccd_effectiveness == 0.0f);
    assert(metrics_no_ccd.num_ccd_contacts == 0);
    assert(metrics_no_ccd.num_penetrations == metrics.num_penetrations);

    std::cout << "  ✓ Populated contact metrics passed" << std::endl;
}

} // namespace

int main() {
    std::cout << "\n========= Collision Validator Tests =========\n" << std::endl;
    test_empty_contact_metrics();
    test_populated_contact_metrics();
    std::cout << "\n========= All Collision Validator Tests Passed =========\n" << std::endl;
    return 0;
}
