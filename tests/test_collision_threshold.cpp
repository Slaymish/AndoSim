#include <cassert>
#include <iostream>
#include <cstdlib>
#include <string>
#include <functional>
#include "collision.h"
#include "rigid_body.h"

using namespace ando_barrier;

static void require(bool condition, const char* message) {
    if (!condition) {
        std::cerr << message << '\n';
        std::exit(1);
    }
}

static void check_built_tree(bool triangles, int count) {
    Mesh mesh;
    State state;
    for (int i = 0; i < count; ++i) {
        int base = state.positions.size();
        state.positions.push_back(Vec3(3 * i, 0, 0));
        state.positions.push_back(Vec3(3 * i + 1, 0, 0));
        state.positions.push_back(Vec3(3 * i, 1, 0));
        if (triangles) mesh.triangles.emplace_back(base, base + 1, base + 2);
        else mesh.edges.emplace_back(base, base + 1);
    }
    // Fresh storage forces the builder through vector reallocations.
    std::vector<BVHNode> nodes;
    std::vector<int> indices;
    if (triangles) Collision::build_triangle_bvh(mesh, state, nodes, indices);
    else Collision::build_edge_bvh(mesh, state, nodes, indices);
    std::vector<int> visited(nodes.size(), 0), primitives(count, 0);
    std::function<void(int)> visit = [&](int index) {
        require(index >= 0 && index < int(nodes.size()), "Invalid BVH child index");
        require(++visited[index] == 1, "BVH cycle or shared child");
        const auto& node = nodes[index];
        if (node.is_leaf()) {
            require(node.left == -1 && node.right == -1, "Leaf has children");
            require(node.prim_idx < count, "Invalid primitive index");
            ++primitives[node.prim_idx];
        } else {
            require(node.prim_idx == -1, "Invalid internal primitive index");
            visit(node.left);
            visit(node.right);
        }
    };
    visit(0);
    for (int hits : primitives) require(hits == 1, "Primitive missing or duplicated");
    for (int hits : visited) require(hits == 1, "Unreachable BVH node");
    require(nodes.size() == size_t(2 * count - 1), "Expected single primitive leaves");
}

static void check_pipeline(bool triangles) {
    Mesh mesh;
    State state;
    if (triangles) {
        // Two separated triangles, each with a nonincident point .02 above it.
        for (int i = 0; i < 2; ++i) {
            int base = state.positions.size();
            Real x = Real(10 * i);
            state.positions.insert(state.positions.end(), {
                Vec3(x - 1, -1, 0), Vec3(x + 1, -1, 0), Vec3(x, 1, 0),
                Vec3(x, 0, Real(0.02))});
            mesh.triangles.emplace_back(base, base + 1, base + 2);
        }
    } else {
        // Two spatially separated pairs, with no shared endpoint indices.
        for (int i = 0; i < 2; ++i) {
            int base = state.positions.size();
            Real x = Real(10 * i);
            state.positions.insert(state.positions.end(), {
                Vec3(x - 1, 0, 0), Vec3(x + 1, 0, 0),
                Vec3(x, -1, Real(0.02)), Vec3(x, 1, Real(0.02))});
            mesh.edges.emplace_back(base, base + 1);
            mesh.edges.emplace_back(base + 2, base + 3);
        }
    }
    std::vector<ContactPair> contacts;
    Collision::detect_all_collisions(mesh, state, contacts);
    require(contacts.empty(), "Default .01 threshold should exclude .02 gaps");
    Collision::detect_all_collisions(mesh, state, contacts, Real(0.05));
    require(contacts.size() == 2, "Configured .05 threshold must find both .02 contacts");
    bool seen[2] = {false, false};
    for (const auto& contact : contacts) {
        require(contact.type == (triangles ? ContactType::POINT_TRIANGLE : ContactType::EDGE_EDGE),
                "Unexpected contact type");
        int group = contact.idx0 / 4;
        require(group >= 0 && group < 2 && !seen[group], "Missing or duplicate contact");
        seen[group] = true;
        require(contact.idx0 == 4 * group + (triangles ? 3 : 0) &&
                contact.idx1 == 4 * group + (triangles ? 0 : 1) &&
                contact.idx2 == 4 * group + (triangles ? 1 : 2) &&
                contact.idx3 == 4 * group + (triangles ? 2 : 3), "Wrong contact primitives");
        require(std::abs(contact.gap - Real(0.02)) < Real(1e-6), "Wrong contact gap");
    }
}

int main(int argc, char** argv) {
    if (argc == 4 && std::string(argv[1]) == "--tree") {
        check_built_tree(std::string(argv[2]) == "triangles", std::stoi(argv[3]));
        return 0;
    }
    if (argc == 3 && std::string(argv[1]) == "--pipeline") {
        check_pipeline(std::string(argv[2]) == "triangles");
        return 0;
    }

    Material material;
    Mesh mesh;
    mesh.initialize({Vec3(-1, -1, 0), Vec3(1, -1, 0), Vec3(0, 1, 0),
                     Vec3(0, 0, Real(0.02))}, {Triangle(0, 1, 2)}, material);
    State state;
    state.initialize(mesh);
    std::vector<ContactPair> contacts;
    Collision::detect_all_collisions(mesh, state, contacts);
    assert(contacts.empty());
    Collision::detect_all_collisions(mesh, state, contacts, Real(0.05));
    assert(contacts.size() == 1);
    assert(contacts[0].type == ContactType::POINT_TRIANGLE);
    assert(contacts[0].idx0 == 3);
    Collision::detect_all_collisions(mesh, state, contacts, Real(0.015));
    assert(contacts.empty());

    RigidBody plate;
    plate.initialize({Vec3(-1, -1, 0), Vec3(1, -1, 0), Vec3(0, 1, 0)},
                     {Triangle(0, 1, 2)}, Real(1000));
    std::vector<RigidBody> bodies = {plate};
    Mesh point_mesh;
    State point_state;
    point_state.positions = {Vec3(0, 0, Real(0.02))};
    Collision::detect_all_collisions(point_mesh, point_state, bodies, contacts);
    assert(contacts.empty());
    Collision::detect_all_collisions(point_mesh, point_state, bodies, contacts, Real(0.05));
    assert(contacts.size() == 1);
    assert(contacts[0].type == ContactType::RIGID_POINT_TRIANGLE);
    Collision::detect_all_collisions(point_mesh, point_state, bodies, contacts, Real(0.015));
    assert(contacts.empty());
    Collision::detect_wall_collisions(point_state, Vec3::UnitZ(), 0, contacts);
    assert(contacts.empty());
    Collision::detect_wall_collisions(point_state, Vec3::UnitZ(), 0, contacts, Real(0.05));
    assert(contacts.size() == 1);
    assert(contacts[0].type == ContactType::WALL);

    // Exercise edge candidate padding with an explicit two-leaf BVH.
    Mesh edges;
    edges.edges = {Edge(0, 1), Edge(2, 3)};
    State edge_state;
    edge_state.positions = {Vec3(-1, 0, 0), Vec3(1, 0, 0),
                            Vec3(0, -1, Real(0.02)), Vec3(0, 1, Real(0.02))};
    std::vector<BVHNode> bvh(3);
    bvh[0].left = 1;
    bvh[0].right = 2;
    for (int i = 0; i < 2; ++i) {
        bvh[i + 1].prim_idx = i;
        bvh[i + 1].bbox.expand(edge_state.positions[2 * i]);
        bvh[i + 1].bbox.expand(edge_state.positions[2 * i + 1]);
        bvh[0].bbox.expand(bvh[i + 1].bbox);
    }
    contacts.clear();
    Collision::broad_phase_edges(edges, edge_state, {}, bvh, contacts);
    assert(contacts.empty());
    Collision::broad_phase_edges(edges, edge_state, {}, bvh, contacts, Real(0.05));
    assert(contacts.size() == 1);
    std::cout << "Collision threshold checks passed\n";
}
