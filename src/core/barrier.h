#pragma once

#include "types.h"
#include "constraints.h"

namespace ando_barrier {

// Cubic barrier energy implementation (Eq. in paper)
// V_weak(g, ḡ, k) = -(k/2)(g-ḡ)² ln(g/ḡ) for g ≤ ḡ, else 0
class Barrier {
public:
    // Energy
    static Real compute_energy(Real g, Real g_max, Real k);
    
    // First derivative w.r.t. g (treating k as constant - semi-implicit)
    static Real compute_gradient(Real g, Real g_max, Real k);
    
    // Second derivative w.r.t. g (treating k as constant)
    static Real compute_hessian(Real g, Real g_max, Real k);
    
    // Check if within barrier domain
    static bool in_domain(Real g, Real g_max);
};

} // namespace ando_barrier
