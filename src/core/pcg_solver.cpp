#include "pcg_solver.h"
#include <iostream>
#include <algorithm>
#include <cmath>

namespace ando_barrier {

bool PCGSolver::solve(const SparseMatrix& A, const VecX& b, VecX& x,
                     Real tol, int max_iters) {
    const int n = static_cast<int>(b.size());
    const int num_vertices = n / 3;
    
    // Build block-Jacobi preconditioner
    std::vector<Mat3> precond;
    build_block_jacobi_preconditioner(A, num_vertices, precond);
    
    // Initial residual: r = b - Ax
    VecX r = b - A * x;
    
    // Check initial convergence
    Real rel_res = compute_relative_residual(r, b);
    if (rel_res < tol) {
        return true;  // Already converged
    }
    
    // Apply preconditioner: z = P⁻¹ r
    VecX z = VecX::Zero(n);
    apply_preconditioner(precond, r, z);
    
    // Initial search direction: p = z
    VecX p = z;
    
    // rz = r^T z
    Real rz_old = r.dot(z);
    
    // PCG iteration
    for (int iter = 0; iter < max_iters; ++iter) {
        // Ap = A * p
        VecX Ap = A * p;
        
        // alpha = (r^T z) / (p^T A p)
        Real pAp = p.dot(Ap);
        if (std::abs(pAp) < 1e-16) {
            std::cerr << "PCG: pAp near zero, matrix may not be SPD" << std::endl;
            return false;
        }
        Real alpha = rz_old / pAp;
        
        // Update solution: x = x + alpha * p
        x += alpha * p;
        
        // Update residual: r = r - alpha * Ap
        r -= alpha * Ap;
        
        // Check convergence
        rel_res = compute_relative_residual(r, b);
        if (rel_res < tol) {
            return true;  // Converged
        }
        
        // Apply preconditioner: z = P⁻¹ r
        apply_preconditioner(precond, r, z);
        
        // beta = (r_new^T z_new) / (r_old^T z_old)
        Real rz_new = r.dot(z);
        Real beta = rz_new / rz_old;
        rz_old = rz_new;
        
        // Update search direction: p = z + beta * p
        p = z + beta * p;
    }
    
    std::cerr << "PCG: Max iterations reached, residual = " << rel_res << std::endl;
    return false;  // Did not converge
}

void PCGSolver::build_block_jacobi_preconditioner(
    const SparseMatrix& A,
    int num_vertices,
    std::vector<Mat3>& precond) {
    
    precond.resize(num_vertices);
    
    // Extract 3×3 diagonal blocks and invert them
    for (int i = 0; i < num_vertices; ++i) {
        Mat3 block = Mat3::Zero();
        
        // Extract 3×3 block for vertex i (rows/cols 3i to 3i+2)
        for (int local_row = 0; local_row < 3; ++local_row) {
            int global_row = 3 * i + local_row;
            
            // Iterate over non-zeros in this row
            for (SparseMatrix::InnerIterator it(A, global_row); it; ++it) {
                int global_col = static_cast<int>(it.col());
                
                // Check if column is in the same 3×3 block
                if (global_col >= 3 * i && global_col < 3 * i + 3) {
                    int local_col = global_col - 3 * i;
                    block(local_row, local_col) = it.value();
                }
            }
        }
        
        // Invert the 3×3 block
        // For SPD matrices, use Cholesky or direct inverse
        Real det = block.determinant();
        if (std::abs(det) > 1e-16) {
            precond[i] = block.inverse();
        } else {
            // Singular block, use identity
            precond[i] = Mat3::Identity();
        }
    }
}

void PCGSolver::apply_preconditioner(
    const std::vector<Mat3>& precond,
    const VecX& r,
    VecX& z) {
    
    const int num_vertices = static_cast<int>(precond.size());
    
    for (int i = 0; i < num_vertices; ++i) {
        // Extract 3-vector from r
        Vec3 r_block(r[3*i], r[3*i+1], r[3*i+2]);
        
        // Apply preconditioner block: z_block = P_i⁻¹ * r_block
        Vec3 z_block = precond[i] * r_block;
        
        // Store result
        z[3*i]   = z_block[0];
        z[3*i+1] = z_block[1];
        z[3*i+2] = z_block[2];
    }
}

Real PCGSolver::compute_relative_residual(const VecX& r, const VecX& b) {
    Real r_inf = r.lpNorm<Eigen::Infinity>();
    Real b_inf = b.lpNorm<Eigen::Infinity>();
    
    if (b_inf < 1e-16) {
        return r_inf;  // Avoid division by zero
    }
    
    return r_inf / b_inf;
}

} // namespace ando_barrier
