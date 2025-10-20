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
#include "energy_tracker.h"
#include "collision_validator.h"
#include "adaptive_timestep.h"

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
        .def_readwrite("velocity_damping", &SimParams::velocity_damping)
        .def_readwrite("contact_restitution", &SimParams::contact_restitution)
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
            for (py::ssize_t i = 0; i < verts_arr.shape(0); ++i) {
                verts.push_back(Vec3(verts_arr(i, 0), verts_arr(i, 1), verts_arr(i, 2)));
            }
            
            std::vector<Triangle> tris;
            for (py::ssize_t i = 0; i < tris_arr.shape(0); ++i) {
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
            for (py::ssize_t i = 0; i < grad.shape(0); ++i) {
                grad(i) = grad_vec(i);
            }
        }, "Compute elastic gradient (forces)")
        .def_static("compute_hessian", &Elasticity::compute_hessian,
             "Compute elastic Hessian (explicit assembly)");
    
    // Barrier energy functions
    m.def("barrier_energy", &Barrier::compute_energy, 
          "Compute cubic barrier energy V_weak(g, g_max, k)");
    m.def("barrier_gradient", &Barrier::compute_gradient,
          "Compute cubic barrier gradient w.r.t. g");
    m.def("barrier_hessian", &Barrier::compute_hessian,
          "Compute cubic barrier Hessian w.r.t. g");
    
    // Mesh creation utilities
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
    
    // EnergyDiagnostics struct
    py::class_<EnergyDiagnostics>(m, "EnergyDiagnostics")
        .def(py::init<>())
        .def_readonly("kinetic_energy", &EnergyDiagnostics::kinetic_energy)
        .def_readonly("elastic_energy", &EnergyDiagnostics::elastic_energy)
        .def_readonly("barrier_energy", &EnergyDiagnostics::barrier_energy)
        .def_readonly("total_energy", &EnergyDiagnostics::total_energy)
        .def_readonly("energy_drift_percent", &EnergyDiagnostics::energy_drift_percent)
        .def_readonly("energy_drift_absolute", &EnergyDiagnostics::energy_drift_absolute)
        .def_property_readonly("linear_momentum", [](const EnergyDiagnostics& d) {
            return std::vector<Real>{d.linear_momentum[0], d.linear_momentum[1], d.linear_momentum[2]};
        })
        .def_property_readonly("angular_momentum", [](const EnergyDiagnostics& d) {
            return std::vector<Real>{d.angular_momentum[0], d.angular_momentum[1], d.angular_momentum[2]};
        })
        .def_readonly("max_velocity", &EnergyDiagnostics::max_velocity)
        .def_readonly("num_contacts", &EnergyDiagnostics::num_contacts)
        .def_readonly("num_pins", &EnergyDiagnostics::num_pins)
        .def("update_drift", &EnergyDiagnostics::update_drift);
    
    // EnergyTracker class
    py::class_<EnergyTracker>(m, "EnergyTracker")
        .def(py::init<>())
        .def_static("compute", &EnergyTracker::compute,
            py::arg("mesh"), py::arg("state"), py::arg("constraints"), py::arg("params"),
            "Compute comprehensive energy diagnostics")
        .def_static("compute_kinetic_energy", &EnergyTracker::compute_kinetic_energy,
            "Compute kinetic energy")
        .def_static("compute_linear_momentum", 
            [](const State& state) {
                Vec3 mom = EnergyTracker::compute_linear_momentum(state);
                return std::vector<Real>{mom[0], mom[1], mom[2]};
            },
            "Compute linear momentum")
        .def_static("compute_angular_momentum",
            [](const State& state) {
                Vec3 ang = EnergyTracker::compute_angular_momentum(state);
                return std::vector<Real>{ang[0], ang[1], ang[2]};
            },
            "Compute angular momentum")
        .def_static("compute_max_velocity", &EnergyTracker::compute_max_velocity,
            "Compute maximum velocity");
    
    // CollisionMetrics struct
    py::class_<CollisionMetrics>(m, "CollisionMetrics")
        .def(py::init<>())
        .def_readonly("num_point_triangle", &CollisionMetrics::num_point_triangle)
        .def_readonly("num_edge_edge", &CollisionMetrics::num_edge_edge)
        .def_readonly("num_wall", &CollisionMetrics::num_wall)
        .def_readonly("num_total_contacts", &CollisionMetrics::num_total_contacts)
        .def_readonly("min_gap", &CollisionMetrics::min_gap)
        .def_readonly("max_gap", &CollisionMetrics::max_gap)
        .def_readonly("avg_gap", &CollisionMetrics::avg_gap)
        .def_readonly("num_penetrations", &CollisionMetrics::num_penetrations)
        .def_readonly("max_penetration", &CollisionMetrics::max_penetration)
        .def_readonly("avg_penetration", &CollisionMetrics::avg_penetration)
        .def_readonly("ccd_enabled", &CollisionMetrics::ccd_enabled)
        .def_readonly("num_ccd_contacts", &CollisionMetrics::num_ccd_contacts)
        .def_readonly("num_broad_phase_contacts", &CollisionMetrics::num_broad_phase_contacts)
        .def_readonly("ccd_effectiveness", &CollisionMetrics::ccd_effectiveness)
        .def_readonly("max_relative_velocity", &CollisionMetrics::max_relative_velocity)
        .def_readonly("avg_relative_velocity", &CollisionMetrics::avg_relative_velocity)
        .def_readonly("has_tunneling", &CollisionMetrics::has_tunneling)
        .def_readonly("has_major_penetration", &CollisionMetrics::has_major_penetration)
        .def_readonly("is_stable", &CollisionMetrics::is_stable)
        .def("quality_level", &CollisionMetrics::quality_level)
        .def("quality_description", &CollisionMetrics::quality_description);
    
    // CollisionValidator class
    py::class_<CollisionValidator>(m, "CollisionValidator")
        .def(py::init<>())
        .def_static("compute_metrics", &CollisionValidator::compute_metrics,
            py::arg("mesh"), py::arg("state"), py::arg("contacts"),
            py::arg("gap_max"), py::arg("ccd_enabled"),
            "Compute comprehensive collision metrics")
        .def_static("has_penetrations",
            [](const std::vector<ContactPair>& contacts) {
                return CollisionValidator::has_penetrations(contacts);
            },
            "Check if any contacts have penetrations")
        .def_static("max_penetration_depth",
            [](const std::vector<ContactPair>& contacts) {
                return CollisionValidator::max_penetration_depth(contacts);
            },
            "Get maximum penetration depth");
    
    // AdaptiveTimestep class
    py::class_<AdaptiveTimestep>(m, "AdaptiveTimestep")
        .def(py::init<>())
        .def_static("compute_next_dt",
            [](const VecX& velocities, const Mesh& mesh, Real current_dt,
               Real dt_min, Real dt_max, Real safety_factor) {
                return AdaptiveTimestep::compute_next_dt(
                    velocities, mesh, current_dt, dt_min, dt_max, safety_factor
                );
            },
            py::arg("velocities"), py::arg("mesh"), py::arg("current_dt"),
            py::arg("dt_min"), py::arg("dt_max"), py::arg("safety_factor") = 0.5,
            "Compute next timestep using CFL condition")
        .def_static("compute_cfl_timestep",
            &AdaptiveTimestep::compute_cfl_timestep,
            py::arg("max_velocity"), py::arg("min_edge_length"), py::arg("safety_factor"),
            "Compute CFL timestep from velocity and mesh resolution")
        .def_static("compute_min_edge_length",
            &AdaptiveTimestep::compute_min_edge_length,
            py::arg("mesh"),
            "Compute minimum edge length in mesh")
        .def_static("compute_max_velocity",
            &AdaptiveTimestep::compute_max_velocity,
            py::arg("velocities"),
            "Compute maximum velocity magnitude");
}

