#!/usr/bin/env python3
"""
Standalone demo of the Ando Barrier elasticity simulation.
Runs without Blender - uses matplotlib for visualization.

This demo shows:
1. Creating a simple mesh (cloth patch)
2. Computing elasticity energy and forces
3. Visualizing the deformation
"""

import sys
import os
import numpy as np

# Try to import matplotlib, but make it optional
try:
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
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


def create_cloth_patch(nx=5, ny=5, size=1.0):
    """
    Create a rectangular cloth mesh.
    
    Args:
        nx: Number of vertices in x direction
        ny: Number of vertices in y direction
        size: Size of the patch
        
    Returns:
        vertices: numpy array (N, 3)
        triangles: numpy array (M, 3) of vertex indices
    """
    vertices = []
    for j in range(ny):
        for i in range(nx):
            x = (i / (nx - 1)) * size
            y = (j / (ny - 1)) * size
            z = 0.0
            vertices.append([x, y, z])
    
    vertices = np.array(vertices, dtype=np.float32)
    
    # Create triangles
    triangles = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            # Each quad becomes two triangles
            v0 = j * nx + i
            v1 = j * nx + (i + 1)
            v2 = (j + 1) * nx + i
            v3 = (j + 1) * nx + (i + 1)
            
            triangles.append([v0, v1, v2])
            triangles.append([v1, v3, v2])
    
    triangles = np.array(triangles, dtype=np.int32)
    
    return vertices, triangles


def visualize_mesh(vertices, triangles, title="Mesh", energies=None):
    """
    Visualize a mesh using matplotlib.
    
    Args:
        vertices: numpy array (N, 3)
        triangles: numpy array (M, 3)
        title: Plot title
        energies: Optional array of per-triangle energies for coloring
    """
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # Plot triangles
    for i, tri in enumerate(triangles):
        v0, v1, v2 = vertices[tri]
        xs = [v0[0], v1[0], v2[0], v0[0]]
        ys = [v0[1], v1[1], v2[1], v0[1]]
        zs = [v0[2], v1[2], v2[2], v0[2]]
        
        if energies is not None:
            # Color by energy
            color = plt.cm.hot(min(1.0, energies[i] / np.max(energies)))
            ax.plot(xs, ys, zs, 'b-', alpha=0.3)
            ax.plot_trisurf([v0[0], v1[0], v2[0]], 
                          [v0[1], v1[1], v2[1]], 
                          [v0[2], v1[2], v2[2]], 
                          color=color, alpha=0.5)
        else:
            ax.plot(xs, ys, zs, 'b-', alpha=0.6)
    
    # Plot vertices
    ax.scatter(vertices[:, 0], vertices[:, 1], vertices[:, 2], 
              c='red', marker='o', s=20, alpha=0.8)
    
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_title(title)
    
    # Equal aspect ratio
    max_range = np.array([
        vertices[:, 0].max() - vertices[:, 0].min(),
        vertices[:, 1].max() - vertices[:, 1].min(),
        vertices[:, 2].max() - vertices[:, 2].min()
    ]).max() / 2.0
    
    mid_x = (vertices[:, 0].max() + vertices[:, 0].min()) * 0.5
    mid_y = (vertices[:, 1].max() + vertices[:, 1].min()) * 0.5
    mid_z = (vertices[:, 2].max() + vertices[:, 2].min()) * 0.5
    
    ax.set_xlim(mid_x - max_range, mid_x + max_range)
    ax.set_ylim(mid_y - max_range, mid_y + max_range)
    ax.set_zlim(mid_z - max_range, mid_z + max_range)
    
    plt.tight_layout()
    return fig, ax


def demo_elasticity():
    """
    Demo: Create a cloth patch and show elastic energy under deformation.
    """
    print("\n" + "="*60)
    print("Demo: Elasticity Energy Computation")
    print("="*60)
    
    # Create a small cloth patch
    print("\n1. Creating 5x5 cloth patch...")
    vertices, triangles = create_cloth_patch(nx=5, ny=5, size=1.0)
    print(f"   Vertices: {len(vertices)}")
    print(f"   Triangles: {len(triangles)}")
    
    # Create mesh object
    print("\n2. Initializing mesh with material properties...")
    mesh = abc.Mesh()
    material = abc.Material()
    material.youngs_modulus = 1e6  # Pa
    material.poisson_ratio = 0.3
    material.density = 1000.0      # kg/m³
    material.thickness = 0.001     # m
    
    mesh.initialize(vertices, triangles, material)
    print(f"   Young's modulus: {material.youngs_modulus} Pa")
    print(f"   Poisson ratio: {material.poisson_ratio}")
    print(f"   Thickness: {material.thickness} m")
    
    # Create state
    state = abc.State()
    state.initialize(mesh)
    
    # Compute energy at rest
    print("\n3. Computing elasticity energy at rest configuration...")
    energy_rest = abc.Elasticity.compute_energy(mesh, state)
    print(f"   Energy at rest: {energy_rest:.6e} J")
    
    # Deform the mesh (stretch top edge)
    print("\n4. Deforming mesh (stretching top edge by 20%)...")
    vertices_deformed = vertices.copy()
    # Find vertices at y=1.0 (top edge) and stretch them
    for i in range(len(vertices)):
        if vertices[i, 1] > 0.99:  # Top edge
            vertices_deformed[i, 0] *= 1.2  # Stretch in x direction
    
    # Update mesh with deformed positions
    mesh.vertices = vertices_deformed
    
    # Compute energy after deformation
    energy_deformed = abc.Elasticity.compute_energy(mesh, state)
    print(f"   Energy after deformation: {energy_deformed:.6e} J")
    print(f"   Energy increase: {energy_deformed - energy_rest:.6e} J")
    
    # Compute gradient (forces)
    print("\n5. Computing elastic forces...")
    gradient = np.zeros(len(vertices) * 3, dtype=np.float32)
    abc.Elasticity.compute_gradient(mesh, state, gradient)
    forces = gradient.reshape(-1, 3)
    
    # Compute force magnitude
    force_magnitudes = np.linalg.norm(forces, axis=1)
    print(f"   Max force magnitude: {np.max(force_magnitudes):.6e} N")
    print(f"   RMS force: {np.sqrt(np.mean(force_magnitudes**2)):.6e} N")
    
    # Visualize
    print("\n6. Generating visualization...")
    
    if not HAS_MATPLOTLIB:
        print("   (Skipping visualization - matplotlib not installed)")
    else:
        # Plot rest configuration
        fig1, ax1 = visualize_mesh(vertices, triangles, 
                                   title="Rest Configuration (E = 0)")
        
        # Plot deformed configuration
        fig2, ax2 = visualize_mesh(vertices_deformed, triangles, 
                                   title=f"Deformed Configuration (E = {energy_deformed:.3e} J)")
        
        # Add force vectors to deformed plot
        scale = 0.05 / (np.max(force_magnitudes) + 1e-10)
        for i in range(len(vertices_deformed)):
            if force_magnitudes[i] > 1e-6:
                ax2.quiver(vertices_deformed[i, 0], vertices_deformed[i, 1], vertices_deformed[i, 2],
                          forces[i, 0], forces[i, 1], forces[i, 2],
                          length=scale*force_magnitudes[i], color='green', 
                          arrow_length_ratio=0.3, linewidth=2)
        
        plt.show()
        print("   (Close plot windows to continue)")
    
    print("\n" + "="*60)
    print("✓ Demo completed successfully!")
    print("="*60)


if __name__ == "__main__":
    demo_elasticity()
