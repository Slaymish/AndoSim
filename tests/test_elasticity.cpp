#include <cmath>
#include <iostream>
#include <vector>

#include "elasticity.h"
#include "pcg_solver.h"
#include <Eigen/Eigenvalues>
#include <string>
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

int main(int argc, char** argv) {
    if (argc == 2 && std::string(argv[1]) == "--hessian") {
        Mesh mesh;
        Material mat;
        mesh.initialize({Vec3(0,0,0),Vec3(1,0,1),Vec3(.4,1,.3)},
                        {Triangle(0,1,2)}, mat);
        State state; state.initialize(mesh);
        std::vector<Triplet> triplets;
        Elasticity::compute_hessian(mesh, state, triplets);
        SparseMatrix sparse(9,9); sparse.setFromTriplets(triplets.begin(),triplets.end());
        MatX H(sparse);
        Eigen::SelfAdjointEigenSolver<MatX> eig(H);
        VecX translation = VecX::Zero(9);
        for (int i=0;i<3;++i) translation[3*i]=1;
        Real error=(H*translation).norm()/H.norm();
        std::cout << "min eigenvalue=" << eig.eigenvalues().minCoeff()
                  << " translation error=" << error << std::endl;
        if (eig.eigenvalues().minCoeff() < -Real(.001) || error > Real(1e-5)) return 1;
        return 0;
    }
    if (argc == 2 && std::string(argv[1]) == "--pcg-scale") {
        // A small SPD system is well-conditioned regardless of RHS magnitude.
        SparseMatrix A(3,3); A.setIdentity();
        VecX b=VecX::Constant(3, Real(1e-9)), x=VecX::Zero(3);
        bool ok=PCGSolver::solve(A,b,x,Real(1e-4),10);
        Real residual=(A*x-b).norm()/b.norm();
        std::cout << "scaled SPD converged=" << ok << " residual=" << residual << std::endl;
        return ok && residual < Real(1e-4) ? 0 : 1;
    }

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

    // Pins must hold. The barrier form of a pin only acts within the barrier
    // range, so a vertex that drifted further used to be released for good and
    // the cloth fell off its pins.
    Mesh pinned_mesh;
    pinned_mesh.initialize(grid(nx, ny, 0.4, 1.0), grid_triangles(nx, ny), material);
    State pinned_state;
    pinned_state.initialize(pinned_mesh);
    Constraints pins;
    std::vector<Index> pinned_vertices;
    for (size_t i = 0; i < pinned_state.positions.size(); ++i) {
        const Vec3& p = pinned_state.positions[i];
        if (std::abs(p[0]) > Real(0.19) && std::abs(p[1]) > Real(0.19)) {
            pins.add_pin(static_cast<Index>(i), p);
            pinned_vertices.push_back(static_cast<Index>(i));
        }
    }
    if (pinned_vertices.empty()) {
        std::cerr << "pin fixture built no pins\n";
        return 1;
    }
    std::vector<Vec3> targets;
    for (Index idx : pinned_vertices) {
        targets.push_back(pinned_state.positions[idx]);
    }

    const Vec3 gravity(0.0, 0.0, -9.81);
    for (int i = 0; i < 200; ++i) {
        for (auto& velocity : pinned_state.velocities) {
            velocity += gravity * params.dt;
        }
        Integrator::step(pinned_mesh, pinned_state, pins, params);
    }
    for (size_t k = 0; k < pinned_vertices.size(); ++k) {
        Real drift = (pinned_state.positions[pinned_vertices[k]] - targets[k]).norm();
        if (drift > Real(1e-6)) {
            std::cerr << "pin drifted " << drift << " m\n";
            return 1;
        }
    }
    Real centre_z = pinned_state.positions[pinned_state.positions.size() / 2][2];
    if (!(centre_z < Real(-0.01))) {
        std::cerr << "unpinned centre did not fall below the pins: " << centre_z << "\n";
        return 1;
    }
    std::cout << "Pins held; centre sagged to z=" << centre_z << std::endl;
    std::cout << "Elasticity checks passed\n";
    return 0;
}
