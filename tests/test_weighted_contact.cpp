#include "mesh.h"
#include "state.h"
#include "constraints.h"
#include "collision.h"
#include "rigid_body.h"
#define private public
#include "integrator.h"
#undef private
#include "friction.h"
#include "stiffness.h"
#include <iostream>
#include <string>
using namespace ando_barrier;

int main(int argc, char** argv) {
    const bool restitution = argc > 1;
    const bool edge = restitution && std::string(argv[1]) == "--restitution-edge";
    Mesh mesh;
    mesh.initialize(edge ? std::vector<Vec3>{Vec3(.505,-2,.505),Vec3(.505,2,.505),Vec3(3,2,1.005)}
                         : std::vector<Vec3>{Vec3(-2,-2,1.005),Vec3(2,-2,1.005),Vec3(0,2,1.005)},
                    {Triangle(0,1,2)}, Material());
    State state; state.initialize(mesh);
    state.masses = {1,2,4};
    if (edge) {
        // Isolate one edge witness from the independent reverse face contacts.
        mesh.triangles.clear();
        mesh.edges = {Edge(0,1)};
    }
    Constraints constraints;
    SimParams params; params.dt=.01; params.contact_gap_max=.02;
    params.enable_friction=true; params.friction_mu=.5;
    ContactPair c; c.type=ContactType::RIGID_POINT_TRIANGLE;
    c.idx0=0; c.idx1=1; c.idx2=2; c.vertex_count=3;
    c.weights={.25,.25,.5,0}; c.normal=Vec3::UnitZ(); c.gap=.005;
    c.witness_p=Vec3(0,0,1.005); c.witness_q=Vec3(0,0,1); c.rigid_body_index=0;
    int failures=0;
    auto check=[&](bool ok, const char* label) {
        std::cout << (ok ? "PASS: " : "FAIL: ") << label << '\n';
        if (!ok) ++failures;
    };
    if (!restitution) {
        // Compare friction on/off to isolate it from elasticity and the barrier.
        for (int count : {2,3}) {
            c.vertex_count=count;
            c.weights=count==2 ? std::array<Real,4>{.25,.75,0,0}
                               : std::array<Real,4>{.25,.25,.5,0};
            for (bool zero : {true,false}) {
                state.positions_prev=state.positions;
                state.positions_prev[0][0]-=.04;
                if (zero) state.positions_prev[count-1][0]+=.04*c.weights[0]/c.weights[count-1];
                VecX target; state.flatten_positions(target);
                VecX on=VecX::Zero(9),off=VecX::Zero(9); SparseMatrix hon(9,9),hoff(9,9);
                params.enable_friction=false;
                Integrator::compute_gradient(mesh,state,target,{c},constraints,params,1,off,nullptr);
                Integrator::assemble_system_matrix(mesh,state,{c},constraints,params,1,hoff,nullptr);
                params.enable_friction=true;
                Integrator::compute_gradient(mesh,state,target,{c},constraints,params,1,on,nullptr);
                Integrator::assemble_system_matrix(mesh,state,{c},constraints,params,1,hon,nullptr);
                VecX delta=on-off;
                if (zero) {
                    std::cout << "support=" << count << " zero-motion gradient=" << delta.transpose() << '\n';
                    check(delta.norm()<1e-5,"zero witness motion has zero friction gradient");
                    check((hon-hoff).norm()<1e-5,"zero witness motion has no friction Hessian");
                } else {
                    check(delta.head<3>().norm()>0,"moving witness generates friction");
                    for (int a=0;a<count;++a) {
                        check((delta.segment<3>(3*a)*c.weights[0]-delta.head<3>()*c.weights[a]).norm()<1e-4,
                              "gradient distributes by support weights");
                        for (int b=0;b<count;++b) {
                            Real value=hon.coeff(3*a,3*b)-hoff.coeff(3*a,3*b);
                            Real base=hon.coeff(0,0)-hoff.coeff(0,0);
                            check(std::abs(value-base*c.weights[a]*c.weights[b]/(c.weights[0]*c.weights[0]))<.02,
                                  "Hessian includes weighted cross blocks");
                        }
                    }
                }
            }
        }
    } else {
        RigidBody sphere;
        sphere.initialize({Vec3(0,0,1),Vec3(1,0,0),Vec3(0,1,0),Vec3(-1,0,0),Vec3(0,-1,0),Vec3(0,0,-1)},
            {Triangle(0,1,2),Triangle(0,2,3),Triangle(0,3,4),Triangle(0,4,1),Triangle(5,2,1),Triangle(5,3,2),Triangle(5,4,3),Triangle(5,1,4)},2);
        std::vector<RigidBody> bodies{sphere};
        auto contacts=Integrator::compute_contacts(mesh,state,&bodies,.02);
        check(contacts.size()==1 && contacts[0].vertex_count==(edge ? 2 : 3),"single rigid contact against cloth support");
        if (contacts.size()!=1) return 1;
        c=contacts[0];
        if (!edge) check(std::abs(c.weights[0]-.25)<1e-5 && std::abs(c.weights[1]-.25)<1e-5 && std::abs(c.weights[2]-.5)<1e-5,"reviewer support weights");
        params.contact_restitution=.5;
        for(auto& v:state.velocities) v=-c.normal;
        Vec3 n=c.normal.normalized(), r=c.witness_q-sphere.position();
        Real denom=1/sphere.mass()+r.cross(n).dot(sphere.inertia_world_inv()*r.cross(n));
        for(int i=0;i<3;++i) denom+=c.weights[i]*c.weights[i]/state.masses[i];
        Real impulse=1.5/denom;
        Integrator::apply_contact_restitution(mesh,constraints,state,params,&bodies);
        Vec3 witness=Vec3::Zero(),momentum=Vec3::Zero();
        for(int i=0;i<3;++i) {
            Vec3 expected=-c.normal+impulse*c.weights[i]/state.masses[i]*n;
            check((state.velocities[i]-expected).norm()<1e-5,"weighted restitution impulse distribution");
            witness+=c.weights[i]*state.velocities[i];
            momentum+=state.masses[i]*(state.velocities[i]+c.normal);
        }
        check(std::abs((witness-bodies[0].velocity_at_point(c.witness_q)).dot(n)-.5)<1e-5,"relative witness restitution velocity");
        check((momentum+bodies[0].mass()*bodies[0].linear_velocity()).norm()<1e-5,"linear momentum conserved");
    }
    return failures ? 1 : 0;
}
