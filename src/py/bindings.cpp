#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>
#include <pybind11/eigen.h>

#include "types.h"
#include "mesh.h"
#include "state.h"
#include "constraints.h"
#include "elasticity.h"
#include "barrier.h"
#include "stiffness.h"
#include "integrator.h"
#include "collision.h"

namespace py = pybind11;
using namespace ando_barrier;

PYBIND11_MODULE(ando_barrier_core, m) {
    m.doc() = "Ando 2024 Cubic Barrier with Elasticity-Inclusive Dynamic Stiffness";
    
    // Version info
    m.def("version", []() {
        return std::string("ando_barrier_core v") + 
               std::to_string(VERSION_MAJOR) + "." +
               std::to_string(VERSION_MINOR) + "." +
               std::to_string(VERSION_PATCH);
    }, "Get version string");
    
    // Material class
    py::class_<Material>(m, "Material")
        .def(py::init<>())
        .def_readwrite("youngs_modulus", &Material::youngs_modulus)
        .def_readwrite("poisson_ratio", &Material::poisson_ratio)
        .def_readwrite("density", &Material::density)
        .def_readwrite("thickness", &Material::thickness)
        .def_readwrite("bending_stiffness", &Material::bending_stiffness);
    
    // SimParams class
    py::class_<SimParams>(m, "SimParams")
        .def(py::init<>())
        .def_readwrite("dt", &SimParams::dt)
        .def_readwrite("beta_max", &SimParams::beta_max)
        .def_readwrite("min_newton_steps", &SimParams::min_newton_steps)
        .def_readwrite("max_newton_steps", &SimParams::max_newton_steps)
        .def_readwrite("pcg_tol", &SimParams::pcg_tol)
        .def_readwrite("pcg_max_iters", &SimParams::pcg_max_iters)
        .def_readwrite("contact_gap_max", &SimParams::contact_gap_max)
        .def_readwrite("wall_gap", &SimParams::wall_gap)
        .def_readwrite("enable_ccd", &SimParams::enable_ccd)
        .def_readwrite("enable_friction", &SimParams::enable_friction)
        .def_readwrite("friction_mu", &SimParams::friction_mu)
        .def_readwrite("friction_epsilon", &SimParams::friction_epsilon)
        .def_readwrite("enable_strain_limiting", &SimParams::enable_strain_limiting)
        .def_readwrite("strain_limit", &SimParams::strain_limit)
        .def_readwrite("strain_tau", &SimParams::strain_tau);
    
    // Triangle class
    py::class_<Triangle>(m, "Triangle")
        .def(py::init<>())
        .def(py::init<Index, Index, Index>())
        .def_property("vertices",
            [](const Triangle& t) { return std::vector<Index>{t.v[0], t.v[1], t.v[2]}; },
            [](Triangle& t, const std::vector<Index>& v) { 
                t.v[0] = v[0]; t.v[1] = v[1]; t.v[2] = v[2]; 
            });
    
    // Mesh class
    py::class_<Mesh>(m, "Mesh")
        .def(py::init<>())
        .def("initialize", [](Mesh& mesh, py::array_t<Real> vertices, py::array_t<int32_t> triangles, const Material& mat) {
            auto verts_arr = vertices.unchecked<2>();
            auto tris_arr = triangles.unchecked<2>();
            
            std::vector<Vec3> verts;
            for (ssize_t i = 0; i < verts_arr.shape(0); ++i) {
                verts.push_back(Vec3(verts_arr(i, 0), verts_arr(i, 1), verts_arr(i, 2)));
            }
            
            std::vector<Triangle> tris;
            for (ssize_t i = 0; i < tris_arr.shape(0); ++i) {
                tris.push_back(Triangle{Index(tris_arr(i, 0)), Index(tris_arr(i, 1)), Index(tris_arr(i, 2))});
            }
            
            mesh.initialize(verts, tris, mat);
        }, "Initialize mesh from numpy arrays")
        .def("num_vertices", &Mesh::num_vertices)
        .def("num_triangles", &Mesh::num_triangles)
        .def("get_vertices", [](const Mesh& mesh) {
            py::array_t<Real> result({mesh.num_vertices(), size_t(3)});
            auto r = result.mutable_unchecked<2>();
            for (size_t i = 0; i < mesh.num_vertices(); ++i) {
                r(i, 0) = mesh.vertices[i][0];
                r(i, 1) = mesh.vertices[i][1];
                r(i, 2) = mesh.vertices[i][2];
            }
            return result;
        })
        .def("set_positions", [](Mesh& mesh, py::array_t<Real> positions) {
            auto pos = positions.unchecked<2>();
            std::vector<Vec3> verts;
            for (size_t i = 0; i < pos.shape(0); ++i) {
                verts.push_back(Vec3(pos(i, 0), pos(i, 1), pos(i, 2)));
            }
            mesh.set_positions(verts);
        })
        .def_property("vertices",
            [](const Mesh& mesh) {
                py::array_t<Real> result({mesh.num_vertices(), size_t(3)});
                auto r = result.mutable_unchecked<2>();
                for (size_t i = 0; i < mesh.num_vertices(); ++i) {
                    r(i, 0) = mesh.vertices[i][0];
                    r(i, 1) = mesh.vertices[i][1];
                    r(i, 2) = mesh.vertices[i][2];
                }
                return result;
            },
            [](Mesh& mesh, py::array_t<Real> positions) {
                auto pos = positions.unchecked<2>();
                for (size_t i = 0; i < pos.shape(0) && i < mesh.num_vertices(); ++i) {
                    mesh.vertices[i][0] = pos(i, 0);
                    mesh.vertices[i][1] = pos(i, 1);
                    mesh.vertices[i][2] = pos(i, 2);
                }
            });
    
    // State class
    py::class_<State>(m, "State")
        .def(py::init<>())
        .def("initialize", &State::initialize)
        .def("num_vertices", &State::num_vertices)
        .def("get_positions", [](const State& state) {
            py::array_t<Real> result({state.num_vertices(), size_t(3)});
            auto r = result.mutable_unchecked<2>();
            for (size_t i = 0; i < state.num_vertices(); ++i) {
                r(i, 0) = state.positions[i][0];
                r(i, 1) = state.positions[i][1];
                r(i, 2) = state.positions[i][2];
            }
            return result;
        })
        .def("get_velocities", [](const State& state) {
            py::array_t<Real> result({state.num_vertices(), size_t(3)});
            auto r = result.mutable_unchecked<2>();
            for (size_t i = 0; i < state.num_vertices(); ++i) {
                r(i, 0) = state.velocities[i][0];
                r(i, 1) = state.velocities[i][1];
                r(i, 2) = state.velocities[i][2];
            }
            return result;
        })
        .def("set_velocities", [](State& state, py::array_t<Real> velocities) {
            auto vel = velocities.unchecked<2>();
            for (size_t i = 0; i < vel.shape(0) && i < state.num_vertices(); ++i) {
                state.velocities[i][0] = vel(i, 0);
                state.velocities[i][1] = vel(i, 1);
                state.velocities[i][2] = vel(i, 2);
            }
        })
        .def("apply_gravity", [](State& state, py::array_t<Real> gravity, Real dt) {
            auto g = gravity.unchecked<1>();
            Vec3 grav(g(0), g(1), g(2));
            for (size_t i = 0; i < state.num_vertices(); ++i) {
                state.velocities[i] += grav * dt;
            }
        }, "Apply gravity acceleration to all vertices");
    
    // Constraints class
    py::class_<Constraints>(m, "Constraints")
        .def(py::init<>())
        .def("add_pin", [](Constraints& c, Index vidx, py::array_t<Real> target) {
            auto t = target.unchecked<1>();
            c.add_pin(vidx, Vec3(t(0), t(1), t(2)));
        })
        .def("add_wall", [](Constraints& c, py::array_t<Real> normal, Real offset, Real gap) {
            auto n = normal.unchecked<1>();
            c.add_wall(Vec3(n(0), n(1), n(2)), offset, gap);
        })
        .def("num_active_pins", &Constraints::num_active_pins)
        .def("num_active_contacts", &Constraints::num_active_contacts);

    // Contact types and data structures
    py::enum_<ContactType>(m, "ContactType")
        .value("POINT_TRIANGLE", ContactType::POINT_TRIANGLE)
        .value("EDGE_EDGE", ContactType::EDGE_EDGE)
        .value("WALL", ContactType::WALL)
        .export_values();

    py::class_<ContactPair>(m, "Contact")
        .def(py::init<>())
        .def_property_readonly("type", [](const ContactPair& c) { return c.type; })
        .def_property_readonly("idx0", [](const ContactPair& c) { return c.idx0; })
        .def_property_readonly("idx1", [](const ContactPair& c) { return c.idx1; })
        .def_property_readonly("idx2", [](const ContactPair& c) { return c.idx2; })
        .def_property_readonly("idx3", [](const ContactPair& c) { return c.idx3; })
        .def_property_readonly("gap", [](const ContactPair& c) { return c.gap; })
        .def_property_readonly("normal", [](const ContactPair& c) { return c.normal; })
        .def_property_readonly("witness_p", [](const ContactPair& c) { return c.witness_p; })
        .def_property_readonly("witness_q", [](const ContactPair& c) { return c.witness_q; });
    
    // Elasticity class (static methods)
    py::class_<Elasticity>(m, "Elasticity")
        .def(py::init<>())
        .def_static("compute_energy", &Elasticity::compute_energy,
             "Compute total elastic energy")
        .def_static("compute_gradient", [](const Mesh& mesh, const State& state, py::array_t<Real> gradient) {
            auto grad = gradient.mutable_unchecked<1>();
            VecX grad_vec(grad.shape(0));
            Elasticity::compute_gradient(mesh, state, grad_vec);
            for (ssize_t i = 0; i < grad.shape(0); ++i) {
                grad(i) = grad_vec(i);
            }
        }, "Compute elastic gradient (forces)")
        .def_static("compute_hessian", &Elasticity::compute_hessian,
             "Compute elastic Hessian (explicit assembly)");
    
    // Barrier energy functions (module-level functions)
    m.def("barrier_energy", &Barrier::compute_energy, 
          "Compute cubic barrier energy V_weak(g, g_max, k)");
    m.def("barrier_gradient", &Barrier::compute_gradient,
          "Compute cubic barrier gradient w.r.t. g");
    m.def("barrier_hessian", &Barrier::compute_hessian,
          "Compute cubic barrier Hessian w.r.t. g");
    
    // Helper functions for creating meshes from Blender
    m.def("create_mesh_from_blender", 
        [](py::array_t<Real> vertices, py::array_t<int32_t> triangles, const Material& mat) {
            auto verts_arr = vertices.unchecked<2>();
            auto tris_arr = triangles.unchecked<2>();
            
            std::vector<Vec3> verts;
            for (size_t i = 0; i < verts_arr.shape(0); ++i) {
                verts.push_back(Vec3(verts_arr(i, 0), verts_arr(i, 1), verts_arr(i, 2)));
            }
            
            std::vector<Triangle> tris;
            for (size_t i = 0; i < tris_arr.shape(0); ++i) {
                tris.push_back(Triangle(tris_arr(i, 0), tris_arr(i, 1), tris_arr(i, 2)));
            }
            
            Mesh mesh;
            mesh.initialize(verts, tris, mat);
            return mesh;
        },
        "Create mesh from numpy arrays (vertices Nx3, triangles Mx3)");
    
    // Integrator class (static methods for simulation)
    py::class_<Integrator>(m, "Integrator")
        .def(py::init<>())
        .def_static("step", &Integrator::step,
            py::arg("mesh"), py::arg("state"), py::arg("constraints"), py::arg("params"),
            "Take one simulation step using Newton integrator with β accumulation")
        .def_static("compute_contacts",
            [](const Mesh& mesh, const State& state) {
                return Integrator::compute_contacts(mesh, state);
            },
            py::arg("mesh"), py::arg("state"),
            "Detect all collision contacts for the current mesh/state");
}
