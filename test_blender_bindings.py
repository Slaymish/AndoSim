#!/usr/bin/env python3
"""
Test script for Ando Barrier Blender integration
Tests Python bindings without requiring Blender
"""

import sys
import os

# Add blender_addon to path
addon_dir = os.path.join(os.path.dirname(__file__), 'blender_addon')
sys.path.insert(0, addon_dir)

import numpy as np
import ando_barrier_core as abc

print("="*60)
print("Testing Ando Barrier Python Bindings")
print("="*60)

# Test 1: Version
print(f"\n✓ Module version: {abc.version()}")

# Test 2: Create material
print("\n[Test 2] Creating material...")
material = abc.Material()
material.youngs_modulus = 1e6
material.poisson_ratio = 0.3
material.density = 1000.0
material.thickness = 0.001
print(f"✓ Material: E={material.youngs_modulus}, ν={material.poisson_ratio}")

# Test 3: Create simple mesh (10x10 cloth)
print("\n[Test 3] Creating 10×10 mesh...")
res = 10
vertices = []
for i in range(res):
    for j in range(res):
        x = (i / (res-1)) - 0.5
        z = (j / (res-1)) - 0.5
        y = 0.5  # Start at height 0.5
        vertices.append([x, y, z])

triangles = []
for i in range(res-1):
    for j in range(res-1):
        v0 = i * res + j
        v1 = v0 + 1
        v2 = v0 + res
        v3 = v2 + 1
        triangles.append([v0, v1, v2])
        triangles.append([v1, v3, v2])

vertices = np.array(vertices, dtype=np.float32)
triangles = np.array(triangles, dtype=np.int32)

print(f"✓ Generated {len(vertices)} vertices, {len(triangles)} triangles")

# Test 4: Initialize mesh
print("\n[Test 4] Initializing mesh...")
mesh = abc.Mesh()
mesh.initialize(vertices, triangles, material)
print(f"✓ Mesh: {mesh.num_vertices()} vertices, {mesh.num_triangles()} triangles")

# Test 5: Initialize state
print("\n[Test 5] Initializing state...")
state = abc.State()
state.initialize(mesh)
print(f"✓ State: {state.num_vertices()} vertices")

# Test 6: Create constraints
print("\n[Test 6] Creating constraints...")
constraints = abc.Constraints()

# Pin corners
constraints.add_pin(0, np.array([vertices[0][0], vertices[0][1], vertices[0][2]], dtype=np.float32))
constraints.add_pin(res-1, np.array([vertices[res-1][0], vertices[res-1][1], vertices[res-1][2]], dtype=np.float32))

# Add ground plane
ground_normal = np.array([0.0, 1.0, 0.0], dtype=np.float32)  # Y-up
constraints.add_wall(ground_normal, 0.0, 0.001)

print(f"✓ Constraints: {constraints.num_active_pins()} pins, ground plane added")

# Test 7: Set up simulation parameters
print("\n[Test 7] Setting up simulation parameters...")
params = abc.SimParams()
params.dt = 0.01  # 10ms
params.beta_max = 0.25
params.max_newton_steps = 8
params.pcg_tol = 1e-3
params.contact_gap_max = 0.001
params.wall_gap = 0.001

print(f"✓ SimParams: dt={params.dt}, β_max={params.beta_max}")

# Test 8: Apply gravity
print("\n[Test 8] Testing gravity application...")
gravity = np.array([0.0, -9.81, 0.0], dtype=np.float32)  # Y-down
state.apply_gravity(gravity, params.dt)
velocities = state.get_velocities()
print(f"✓ Gravity applied: avg velocity = {np.mean(velocities[:, 1]):.4f} m/s")

# Test 9: Run simulation step
print("\n[Test 9] Running simulation step...")
initial_positions = state.get_positions()
print(f"  Initial height (avg): {np.mean(initial_positions[:, 1]):.4f} m")

abc.Integrator.step(mesh, state, constraints, params)

final_positions = state.get_positions()
print(f"  Final height (avg): {np.mean(final_positions[:, 1]):.4f} m")
print(f"✓ Simulation step completed")

# Test 10: Multiple steps
print("\n[Test 10] Running 10 simulation steps...")
for i in range(10):
    state.apply_gravity(gravity, params.dt)
    abc.Integrator.step(mesh, state, constraints, params)
    if (i+1) % 5 == 0:
        positions = state.get_positions()
        print(f"  Step {i+1}: avg height = {np.mean(positions[:, 1]):.4f} m")

print(f"✓ Multi-step simulation completed")

print("\n" + "="*60)
print("✅ All tests passed!")
print("="*60)
print("\nReady for Blender integration!")
print("Next step: Install add-on in Blender and test bake operator")
