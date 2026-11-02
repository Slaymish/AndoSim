#include <cmath>
#include <iostream>
#include <vector>

#include "elasticity.h"
#include "integrator.h"
#include "mesh.h"
#include "state.h"

using namespace ando_barrier;

namespace {

std::vector<Vec3> grid(int nx, int ny, Real size, Real scale_x) {
    std::vector<Vec3> verts;
    for (int j = 0; j < ny; ++j) {
        for (int i = 0; i < nx; ++i) {
            Real x = (Real(i) / Real(nx - 1) - Real(0.5)) * size * scale_x;
            Real y = (Real(j) / Real(ny - 1) - Real(0.5)) * size;
            verts.push_back(Vec3(x, y, 0.0));
        }
    }
    return verts;
}

std::vector<Triangle> grid_triangles(int nx, int ny) {
    std::vector<Triangle> tris;
    for (int j = 0; j < ny - 1; ++j) {
        for (int i = 0; i < nx - 1; ++i) {
            int a = j * nx + i;
            tris.push_back(Triangle(a, a + 1, a + nx + 1));
            tris.push_back(Triangle(a + 1, a + nx, a + nx + 1));
        }
    }
    return tris;
}

Real mean_edge(const std::vector<Vec3>& p, const std::vector<Triangle>& tris) {
    Real total = 0.0;
    int count = 0;
    for (const auto& t : tris) {
        for (int k = 0; k < 3; ++k) {
            const Vec3& a = p[t.v[k]];
            const Vec3& b = p[t.v[(k + 1) % 3]];
            total += (a - b).norm();
            ++count;
        }
    }
    return total / Real(count);
}

} // namespace

int main() {
    // A membrane stretched 50% beyond its rest length must contract. The rest
    // pose lives in the mesh; the current pose lives in the state.
    const int nx = 5, ny = 5;
    Material material;

    Mesh rest_mesh;
    rest_mesh.initialize(grid(nx, ny, 0.4, 1.0), grid_triangles(nx, ny), material);

    Mesh stretched_mesh;
    stretched_mesh.initialize(grid(nx, ny, 0.4, 1.5), grid_triangles(nx, ny), material);

    State state;
    state.initialize(stretched_mesh);

    const std::vector<Triangle> tris = grid_triangles(nx, ny);
    const Real before = mean_edge(state.positions, tris);
    const Real energy_before = Elasticity::compute_energy(rest_mesh, state);

    SimParams params;
    params.dt = 0.001;
    params.enable_friction = false;
    params.enable_strain_limiting = false;
    params.velocity_damping = 0.0;
    Constraints constraints;

    for (int i = 0; i < 100; ++i) {
        Integrator::step(rest_mesh, state, constraints, params);
    }

    const Real after = mean_edge(state.positions, tris);
    const Real energy_after = Elasticity::compute_energy(rest_mesh, state);

    std::cout << "mean edge before=" << before << " after=" << after
              << " energy before=" << energy_before << " after=" << energy_after << std::endl;

    if (energy_before <= 0.0) {
        std::cerr << "stretched configuration must have positive elastic energy\n";
        return 1;
    }
    if (!(after < before * Real(0.99))) {
        std::cerr << "stretched sheet did not contract: elastic force is not acting\n";
        return 1;
    }
    if (!(energy_after < energy_before * Real(0.9))) {
        std::cerr << "elastic energy did not decrease\n";
        return 1;
    }
    std::cout << "Elasticity checks passed\n";
    return 0;
}
