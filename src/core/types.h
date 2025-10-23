#pragma once

#include <Eigen/Dense>
#include <Eigen/Sparse>
#include <vector>
#include <cstdint>

namespace ando_barrier {

// Precision control - default to single precision for core operations
// Host-side scalars (PCG alphas/betas) can use double
#ifdef USE_DOUBLE_PRECISION
    using Real = double;
#else
    using Real = float;
#endif

using HostScalar = double; // Always use double for critical host scalars

// Eigen types
using Vec3 = Eigen::Matrix<Real, 3, 1>;
using Vec2 = Eigen::Matrix<Real, 2, 1>;
using Mat3 = Eigen::Matrix<Real, 3, 3>;
using Mat2 = Eigen::Matrix<Real, 2, 2>;
using VecX = Eigen::Matrix<Real, Eigen::Dynamic, 1>;
using MatX = Eigen::Matrix<Real, Eigen::Dynamic, Eigen::Dynamic>;

using SparseMatrix = Eigen::SparseMatrix<Real, Eigen::RowMajor>;
using Triplet = Eigen::Triplet<Real>;

// Index types
using Index = int32_t;
using IndexVec = std::vector<Index>;

// Triangle/Edge connectivity
struct Triangle {
    Index v[3];
    
    Triangle() : v{-1, -1, -1} {}
    Triangle(Index i0, Index i1, Index i2) : v{i0, i1, i2} {}
};

struct Edge {
    Index v[2];
    
    Edge() : v{-1, -1} {}
    Edge(Index i0, Index i1) : v{i0, i1} {}
};

// Material properties
struct Material {
    Real youngs_modulus = 1e6;      // E (Pa)
    Real poisson_ratio = 0.3;       // ν
    Real density = 1000.0;          // ρ (kg/m³)
    Real thickness = 0.001;         // h (m) for shells
    Real bending_stiffness = 0.0;   // Optional explicit bending
};

// Simulation parameters (default values per paper)
struct SimParams {
    Real dt = 0.002;                // Δt = 2 ms
    Real beta_max = 0.25;           // β_max for accumulation
    int min_newton_steps = 2;
    int max_newton_steps = 8;

    // When friction is active we fall back to a higher Newton count (Eq. 11)
    int friction_min_newton_steps = 32;

    // PCG parameters
    Real pcg_tol = 1e-3;            // Relative L∞ tolerance
    int pcg_max_iters = 1000;

    // Contact parameters
    Real contact_gap_max = 0.001;   // ḡ = 1 mm default
    Real wall_gap = 0.001;          // g_wall for walls
    bool enable_ccd = true;
    Real contact_normal_epsilon = 1e-8; // Normal normalization guard
    Real barrier_tolerance = 1e-12;      // Triplet drop tolerance

    // Friction (optional)
    bool enable_friction = false;
    Real friction_mu = 0.1;
    Real friction_epsilon = 1e-5;   // 0.01 mm
    Real friction_tangent_threshold = 1e-6;

    // Global damping and restitution controls
    Real velocity_damping = 0.0;     // Fraction of velocity removed each step
    Real contact_restitution = 0.0;  // 0 = inelastic, 1 = fully elastic

    // Strain limiting (optional)
    bool enable_strain_limiting = false;
    Real strain_limit = 0.05;       // 5% default
    Real strain_tau = 0.05;         // τ = strain_limit
    Real strain_epsilon = 0.0;      // ε (will be computed)
    Real strain_svd_epsilon = 1e-6; // SVD regularization threshold

    // Numerical safeguards
    Real hessian_epsilon = 1e-8;    // For SPD enforcement
    Real min_gap = 1e-8;            // Minimum gap for numerical stability
};

// Version info
constexpr int VERSION_MAJOR = 1;
constexpr int VERSION_MINOR = 0;
constexpr int VERSION_PATCH = 0;

} // namespace ando_barrier
