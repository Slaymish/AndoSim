# Standalone Python Demos

This directory contains standalone Python demonstration scripts that can run the Ando Barrier physics simulation **without Blender**. These demos are useful for:

- Testing the C++ core functionality
- Understanding the physics algorithms
- Debugging and development
- Educational purposes

## Prerequisites

1. **Build the project first:**
   ```bash
   cd ..
   ./build.sh
   ```

2. **Install Python dependencies:**
   ```bash
   pip install numpy matplotlib
   ```

## Available Demos

### 1. Barrier Functions Demo (`demo_barrier.py`)

Visualizes the cubic barrier energy, gradient, and Hessian as functions of gap distance.

**Run:**
```bash
python demo_barrier.py
```

**What it shows:**
- Barrier energy curve V(g, ḡ, k)
- Barrier gradient (repulsive force)
- Barrier Hessian (contact stiffness)
- C² smoothness at the boundary g = ḡ
- Active/inactive regions

### 2. Elasticity Demo (`demo_elasticity.py`)

Demonstrates ARAP elasticity energy and forces on a deformable cloth mesh.

**Run:**
```bash
python demo_elasticity.py
```

**What it shows:**
- Creating a cloth mesh (5×5 grid)
- Computing rest-state configuration
- Deforming the mesh (stretching)
- Computing elastic energy and forces
- 3D visualization with force vectors

**Features:**
- Mesh initialization from numpy arrays
- Material properties (Young's modulus, Poisson ratio)
- Energy computation at rest and under deformation
- Gradient (force) computation
- Interactive 3D visualization

## Output Examples

### Barrier Demo
```
Barrier parameters:
  g_max (barrier domain): 1.0
  k (stiffness): 100.0

Barrier properties:
  Active domain: g ∈ (0, 1.0)
  Max energy: 1.839e+01
  Max gradient magnitude: 1.506e+02
  Max Hessian: 1.041e+03
```

### Elasticity Demo
```
1. Creating 5x5 cloth patch...
   Vertices: 25
   Triangles: 32

2. Initializing mesh with material properties...
   Young's modulus: 1000000.0 Pa
   Poisson ratio: 0.3
   Thickness: 0.001 m

3. Computing elasticity energy at rest configuration...
   Energy at rest: 0.000000e+00 J

4. Deforming mesh (stretching top edge by 20%)...
   Energy after deformation: 5.123456e-03 J
   Energy increase: 5.123456e-03 J

5. Computing elastic forces...
   Max force magnitude: 2.456789e-02 N
   RMS force: 8.901234e-03 N
```

## Writing Your Own Demos

Here's a minimal template:

```python
#!/usr/bin/env python3
import sys
import os
import numpy as np

# Add build directory to path
build_dir = os.path.join(os.path.dirname(__file__), '..', 'build')
sys.path.insert(0, build_dir)

import ando_barrier_core as abc

# Create mesh
vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32)
triangles = np.array([[0, 1, 2]], dtype=np.int32)

# Initialize
mesh = abc.Mesh()
material = abc.Material()
material.youngs_modulus = 1e6
mesh.initialize(vertices, triangles, material)

# Compute
elasticity = abc.Elasticity()
energy = elasticity.compute_energy(mesh, abc.State())
print(f"Energy: {energy}")
```

## API Reference

### Core Classes

- **`abc.Mesh()`**: Mesh representation with rest-state data
  - `.initialize(vertices, triangles, material)`
  - `.vertices`: Current vertex positions (N×3)
  - `.compute_F(face_idx)`: Deformation gradient for face

- **`abc.Material()`**: Material properties
  - `.youngs_modulus`: Young's modulus (Pa)
  - `.poisson_ratio`: Poisson ratio (dimensionless)
  - `.density`: Density (kg/m³)
  - `.thickness`: Shell thickness (m)

- **`abc.State()`**: Physics state
  - `.initialize(mesh)`
  - `.positions`, `.velocities`, `.masses`

- **`abc.Elasticity()`**: Elasticity energy and forces
  - `.compute_energy(mesh, state) -> float`
  - `.compute_gradient(mesh, state, gradient_out)`
  - `.compute_hessian(mesh, state, triplets_out)`

- **`abc.Barrier()`**: Cubic barrier functions
  - `.compute_energy(g, g_max, k) -> float`
  - `.compute_gradient(g, g_max, k) -> float`
  - `.compute_hessian(g, g_max, k) -> float`

## Troubleshooting

**Import Error:**
```
ImportError: No module named 'ando_barrier_core'
```
→ Build the project first: `cd .. && ./build.sh`

**Missing matplotlib:**
```
ModuleNotFoundError: No module named 'matplotlib'
```
→ Install: `pip install matplotlib`

**Shared library error:**
```
ImportError: ... ando_barrier_core.cpython-*.so: cannot open shared object file
```
→ Make sure you're running from the `demos/` directory or adjust the `sys.path` correctly.

## Next Steps

- **Task 4+**: These demos will be extended as more features are implemented (dynamic stiffness, contacts, time integration)
- **Visualization**: Consider adding export to common formats (OBJ, VTK) for external visualization
- **Animation**: Add time-stepping demos once the integrator is complete

## License

Same as parent project (see ../LICENSE if applicable).
