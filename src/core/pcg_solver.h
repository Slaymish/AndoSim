#pragma once

#include "types.h"
#include <vector>

namespace ando_barrier {

/**
 * Preconditioned Conjugate Gradient solver with block-Jacobi preconditioner
 * 
 * Solves: A x = b for SPD matrix A
 * Uses 3×3 block-Jacobi preconditioner (diagonal blocks only)
 */
class PCGSolver {
public:
    /**
     * Solve linear system using PCG
     * 
     * @param A System matrix (must be SPD)
     * @param b Right-hand side
     * @param x Solution vector (input: initial guess, output: solution)
     * @param tol Relative residual tolerance (L∞ norm)
     * @param max_iters Maximum iterations
     * @return true if converged, false if max iterations reached
     */
    static bool solve(const SparseMatrix& A, const VecX& b, VecX& x,
                     Real tol = 1e-3, int max_iters = 100);

private:
    /**
     * Build 3×3 block-Jacobi preconditioner
     * 
     * Extracts 3×3 diagonal blocks from A and inverts them
     * 
     * @param A System matrix
     * @param num_vertices Number of vertices (matrix is 3n × 3n)
     * @param precond Output: vector of 3×3 inverse blocks
     */
    static void build_block_jacobi_preconditioner(
        const SparseMatrix& A,
        int num_vertices,
        std::vector<Mat3>& precond
    );
    
    /**
     * Apply block-Jacobi preconditioner: z = P⁻¹ r
     * 
     * @param precond Vector of 3×3 inverse blocks
     * @param r Residual vector
     * @param z Output: preconditioned residual
     */
    static void apply_preconditioner(
        const std::vector<Mat3>& precond,
        const VecX& r,
        VecX& z
    );
    
    /**
     * Compute L∞ norm of relative residual: ||r||_∞ / ||b||_∞
     * 
     * @param r Residual vector
     * @param b Right-hand side
     * @return Relative residual in L∞ norm
     */
    static Real compute_relative_residual(const VecX& r, const VecX& b);
};

} // namespace ando_barrier
