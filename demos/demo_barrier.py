#!/usr/bin/env python3
"""
Standalone demo of the Ando Barrier cubic barrier function.
Runs without Blender - uses matplotlib for visualization.

This demo shows:
1. Barrier energy as a function of gap
2. Barrier gradient (force) as a function of gap
3. Barrier Hessian (stiffness) as a function of gap
"""

import sys
import os
import numpy as np

# Try to import matplotlib, but make it optional
try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib not found. Visualization will be disabled.")
    print("Install with: pip install matplotlib")

# Add the build directory to path to import the C++ module
build_dir = os.path.join(os.path.dirname(__file__), '..', 'build')
sys.path.insert(0, build_dir)

try:
    import ando_barrier_core as abc
    print(f"✓ Loaded ando_barrier_core version: {abc.version()}")
except ImportError as e:
    print(f"✗ Failed to import ando_barrier_core: {e}")
    print(f"  Make sure to build the project first: ./build.sh")
    sys.exit(1)


def demo_barrier_functions():
    """
    Demo: Visualize the cubic barrier energy, gradient, and Hessian.
    """
    print("\n" + "="*60)
    print("Demo: Cubic Barrier Functions")
    print("="*60)
    
    # Barrier parameters
    g_max = 1.0  # Maximum gap (barrier domain)
    k = 100.0    # Stiffness
    
    print(f"\nBarrier parameters:")
    print(f"  g_max (barrier domain): {g_max}")
    print(f"  k (stiffness): {k}")
    
    # Create gap values
    g_values = np.linspace(0.01, 1.5 * g_max, 500)
    
    # Compute barrier quantities
    energies = np.zeros_like(g_values)
    gradients = np.zeros_like(g_values)
    hessians = np.zeros_like(g_values)
    
    for i, g in enumerate(g_values):
        energies[i] = abc.barrier_energy(g, g_max, k)
        gradients[i] = abc.barrier_gradient(g, g_max, k)
        hessians[i] = abc.barrier_hessian(g, g_max, k)
    
    # Find where barrier is active
    active_mask = g_values < g_max
    
    print(f"\nBarrier properties:")
    print(f"  Active domain: g ∈ (0, {g_max})")
    print(f"  Max energy: {np.max(energies):.6e}")
    print(f"  Max gradient magnitude: {np.max(np.abs(gradients)):.6e}")
    print(f"  Max Hessian: {np.max(hessians):.6e}")
    
    # Create visualization (if matplotlib available)
    if not HAS_MATPLOTLIB:
        print("\n(Skipping visualization - matplotlib not installed)")
    else:
        fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    
        # Plot 1: Energy
        ax = axes[0]
        ax.plot(g_values[active_mask], energies[active_mask], 'b-', linewidth=2, label='Active (g < ḡ)')
        ax.plot(g_values[~active_mask], energies[~active_mask], 'r--', linewidth=2, label='Inactive (g ≥ ḡ)')
        ax.axvline(g_max, color='k', linestyle=':', linewidth=1.5, alpha=0.7, label='g = ḡ (boundary)')
        ax.set_xlabel('Gap g', fontsize=12)
        ax.set_ylabel('Barrier Energy V(g)', fontsize=12)
        ax.set_title('Cubic Barrier Energy: V = -(k/2)(g-ḡ)² ln(g/ḡ)', fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Plot 2: Gradient (force)
        ax = axes[1]
        ax.plot(g_values[active_mask], gradients[active_mask], 'b-', linewidth=2, label='Active (g < ḡ)')
        ax.plot(g_values[~active_mask], gradients[~active_mask], 'r--', linewidth=2, label='Inactive (g ≥ ḡ)')
        ax.axvline(g_max, color='k', linestyle=':', linewidth=1.5, alpha=0.7, label='g = ḡ (boundary)')
        ax.axhline(0, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)
        ax.set_xlabel('Gap g', fontsize=12)
        ax.set_ylabel('Barrier Gradient dV/dg (Force)', fontsize=12)
        ax.set_title('Barrier Gradient (Repulsive Force)', fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Plot 3: Hessian (stiffness)
        ax = axes[2]
        ax.plot(g_values[active_mask], hessians[active_mask], 'b-', linewidth=2, label='Active (g < ḡ)')
        ax.plot(g_values[~active_mask], hessians[~active_mask], 'r--', linewidth=2, label='Inactive (g ≥ ḡ)')
        ax.axvline(g_max, color='k', linestyle=':', linewidth=1.5, alpha=0.7, label='g = ḡ (boundary)')
        ax.axhline(0, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)
        ax.set_xlabel('Gap g', fontsize=12)
        ax.set_ylabel('Barrier Hessian d²V/dg² (Stiffness)', fontsize=12)
        ax.set_title('Barrier Hessian (Contact Stiffness)', fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        plt.tight_layout()
    
    # Print some key values
    print(f"\nKey values at selected gaps:")
    test_gaps = [0.1, 0.5, 0.9, 0.99, 1.0, 1.1]
    print(f"{'Gap g':>8} {'Energy':>12} {'Gradient':>12} {'Hessian':>12}")
    print("-" * 48)
    for g in test_gaps:
        e = abc.barrier_energy(g, g_max, k)
        grad = abc.barrier_gradient(g, g_max, k)
        hess = abc.barrier_hessian(g, g_max, k)
        print(f"{g:8.2f} {e:12.4e} {grad:12.4e} {hess:12.4e}")
    
    if HAS_MATPLOTLIB:
        plt.show()
        print("\n(Close the plot window to continue)")
    else:
        print("\n(Visualization skipped - matplotlib not available)")
    
    print("\n" + "="*60)
    print("✓ Demo completed successfully!")
    print("="*60)


if __name__ == "__main__":
    demo_barrier_functions()
