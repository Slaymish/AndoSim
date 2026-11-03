#include "elasticity.h"
#include "stiffness.h"
#include <Eigen/Eigenvalues>

namespace ando_barrier {

Real Elasticity::compute_energy(const Mesh& mesh, const State& state) {
    Real energy = 0.0;
    
    for (size_t i = 0; i < mesh.num_triangles(); ++i) {
        Mat2 F = mesh.compute_F(i, state.positions);
        energy += face_energy(F, mesh.material, mesh.rest_areas[i]);
    }
    
    return energy;
}

void Elasticity::compute_gradient(const Mesh& mesh, const State& state, VecX& gradient) {
    gradient.setZero();
    
    for (size_t i = 0; i < mesh.num_triangles(); ++i) {
        const Triangle& tri = mesh.triangles[i];
        
        // Get current F
        Mat2 F = mesh.compute_F(i, state.positions);
        
        // Compute PK1 stress: P = k * 2 * (F - I)
        Real mu = mesh.material.youngs_modulus / (2.0 * (1.0 + mesh.material.poisson_ratio));
        Real k = mesh.rest_areas[i] * mesh.material.thickness * mu;
        Mat2 I = Mat2::Identity();
        Mat2 P = 2.0 * k * (F - I);
        
        // H = P * Dm_inv^T gives force gradient in material coordinates
        Mat2 H = P * mesh.Dm_inv[i].transpose();
        
        // Local frame of the *current* triangle, used to map the material-space
        // force back to 3D.
        const Vec3& v0 = state.positions[tri.v[0]];
        const Vec3& v1 = state.positions[tri.v[1]];
        const Vec3& v2 = state.positions[tri.v[2]];
        
        Vec3 e1 = v1 - v0;
        Vec3 e2 = v2 - v0;
        Vec3 n = e1.cross(e2);
        n.normalize();
        Vec3 t1 = e1.normalized();
        Vec3 t2 = n.cross(t1);
        
        // Map 2D forces back to 3D using the local frame
        // These are the forces on v1 and v2 (relative to v0)
        Vec3 f1_3d = H(0, 0) * t1 + H(1, 0) * t2;
        Vec3 f2_3d = H(0, 1) * t1 + H(1, 1) * t2;
        Vec3 f0_3d = -(f1_3d + f2_3d);
        
        // Accumulate to global gradient (gradient = -force for energy minimization)
        for (int k = 0; k < 3; ++k) {
            gradient[tri.v[0] * 3 + k] += f0_3d[k];
            gradient[tri.v[1] * 3 + k] += f1_3d[k];
            gradient[tri.v[2] * 3 + k] += f2_3d[k];
        }
    }
}

void Elasticity::compute_hessian(const Mesh& mesh, const State& state,
                                 std::vector<Triplet>& triplets) {
    for (size_t i = 0; i < mesh.num_triangles(); ++i) {
        const Triangle& tri = mesh.triangles[i];
        Mat2 F = mesh.compute_F(i, state.positions);
        
        Mat3 H[3][3];
        face_hessian(F, mesh.material, mesh.rest_areas[i], mesh.Dm_inv[i], H);
        
        // Add to triplet list
        for (int a = 0; a < 3; ++a) {
            for (int b = 0; b < 3; ++b) {
                Index ia = tri.v[a];
                Index ib = tri.v[b];
                
                // The complete element is PSD. Projecting off-diagonal blocks
                // independently destroys its translation nullspace.
                const Mat3& H_spd = H[a][b];
                
                // Add 3×3 block
                for (int k = 0; k < 3; ++k) {
                    for (int l = 0; l < 3; ++l) {
                        triplets.push_back(Triplet(ia * 3 + k, ib * 3 + l, H_spd(k, l)));
                    }
                }
            }
        }
    }
}

Real Elasticity::face_energy(const Mat2& F, const Material& mat, Real area) {
    // ARAP-style energy: E = k * ||F - I||_F^2
    // where k = (area * thickness * E) / (2 * (1 + ν))
    Real mu = mat.youngs_modulus / (2.0 * (1.0 + mat.poisson_ratio));
    Real k = area * mat.thickness * mu;
    
    Mat2 I = Mat2::Identity();
    Mat2 diff = F - I;
    
    return k * diff.squaredNorm();
}

void Elasticity::face_gradient(const Mat2& F, const Material& mat, Real area,
                               const Mat2& Dm_inv, Vec3 grad[3]) {
    // ARAP energy: E = k * ||F - I||²
    // Gradient: ∂E/∂x = 2k * (F - I) : ∂F/∂x
    
    Real mu = mat.youngs_modulus / (2.0 * (1.0 + mat.poisson_ratio));
    Real k = area * mat.thickness * mu;
    
    Mat2 I = Mat2::Identity();
    Mat2 P = 2.0 * k * (F - I);  // First Piola-Kirchhoff stress
    
    // H = P * Dm_inv^T gives forces in material coordinates
    // Map to 3D vertex positions using the local frame
    Mat2 H = P * Dm_inv.transpose();
    
    // For a triangle with vertices v0, v1, v2:
    // F = Ds * Dm_inv where Ds = [e1_2d | e2_2d]
    // e1 = v1 - v0, e2 = v2 - v0
    // The gradient is distributed as:
    // grad[1] = H.col(0), grad[2] = H.col(1), grad[0] = -(grad[1] + grad[2])
    
    // Embed 2D gradients in 3D by extending with zero z-component
    Vec3 g1 = Vec3(H(0, 0), H(1, 0), 0.0);
    Vec3 g2 = Vec3(H(0, 1), H(1, 1), 0.0);
    
    grad[1] = g1;
    grad[2] = g2;
    grad[0] = -(g1 + g2);
}

void Elasticity::face_hessian(const Mat2& F, const Material& mat, Real area,
                              const Mat2& Dm_inv, Mat3 H[3][3]) {
    // Rotation-invariant PSD membrane approximation: edge gradients form a
    // Gram matrix. Preserve negative off-diagonal blocks and zero row sums.
    // This is a solver approximation, not the exact derivative of the moving
    // material frame used by compute_gradient.
    Real mu = mat.youngs_modulus / (2.0 * (1.0 + mat.poisson_ratio));
    Real k = area * mat.thickness * mu;
    Mat2 K = Real(2) * k * (Dm_inv * Dm_inv.transpose());
    H[1][1] = K(0,0) * Mat3::Identity();
    H[2][2] = K(1,1) * Mat3::Identity();
    H[1][2] = H[2][1] = K(0,1) * Mat3::Identity();
    H[0][1] = H[1][0] = -H[1][1] - H[1][2];
    H[0][2] = H[2][0] = -H[2][2] - H[1][2];
    H[0][0] = -H[0][1] - H[0][2];
}

} // namespace ando_barrier
