#pragma once

#include "types.h"
#include "mesh.h"
#include "state.h"

namespace ando_barrier {

// Shell elasticity energy, gradient, and Hessian computation
// Supports ARAP or Baraff-Witkin FE
class Elasticity {
public:
    Elasticity() = default;
    
    // Compute total elastic energy
    static Real compute_energy(const Mesh& mesh, const State& state);
    
    // Compute elastic gradient (forces)
    static void compute_gradient(const Mesh& mesh, const State& state, VecX& gradient);
    
    // Compute elastic Hessian (explicit assembly)
    static void compute_hessian(const Mesh& mesh, const State& state, 
                               std::vector<Triplet>& triplets);
    
    // Enforce SPD by symmetrization and eigenvalue clamping
    static void enforce_spd(Mat3& H, Real epsilon = 1e-8);
    
private:
    // Per-face energy and derivatives (ARAP-style)
    static Real face_energy(const Mat2& F, const Material& mat, Real area);
    static void face_gradient(const Mat2& F, const Material& mat, Real area,
                             const Mat2& Dm_inv, Vec3 grad[3]);
    static void face_hessian(const Mat2& F, const Material& mat, Real area,
                            const Mat2& Dm_inv, Mat3 H[3][3]);
};

} // namespace ando_barrier
