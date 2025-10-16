#include "barrier.h"
#include <cmath>

namespace ando_barrier {

Real Barrier::compute_energy(Real g, Real g_max, Real k) {
    if (g >= g_max || g <= 0.0) return 0.0;
    
    // V_weak(g, ḡ, k) = -(k/2)(g-ḡ)² ln(g/ḡ)
    Real diff = g - g_max;
    Real ln_ratio = std::log(g / g_max);
    
    return -0.5 * k * diff * diff * ln_ratio;
}

Real Barrier::compute_gradient(Real g, Real g_max, Real k) {
    if (g >= g_max || g <= 0.0) return 0.0;
    
    // d/dg V_weak = -k * (g - ḡ) * ln(g/ḡ) - k/2 * (g - ḡ)² / g
    Real diff = g - g_max;
    Real ln_ratio = std::log(g / g_max);
    
    return -k * diff * ln_ratio - 0.5 * k * diff * diff / g;
}

Real Barrier::compute_hessian(Real g, Real g_max, Real k) {
    if (g >= g_max || g <= 0.0) return 0.0;
    
    // d²/dg² V_weak = -k·ln(g/ḡ) - 2k(g-ḡ)/g + (k/2)(g-ḡ)²/g²
    Real diff = g - g_max;
    Real ln_ratio = std::log(g / g_max);
    
    return -k * ln_ratio - 2.0 * k * diff / g + 0.5 * k * diff * diff / (g * g);
}

bool Barrier::in_domain(Real g, Real g_max) {
    return g > 0.0 && g < g_max;
}

} // namespace ando_barrier
