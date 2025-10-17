#!/usr/bin/env python3
"""
Demo 2: Tablecloth Pull
Classic physics demo - pull tablecloth from under objects
Tests: Contact dynamics, friction, precise collision handling
"""

import numpy as np
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))

import ando_barrier_core as abc
from demo_framework import PhysicsDemo, create_grid_mesh, create_cloth_material


class TableclothPullDemo(PhysicsDemo):
    """Tablecloth being pulled rapidly across a table"""
    
    def __init__(self):
        super().__init__(
            name="Tablecloth Pull",
            description="Cloth pulled rapidly from table edge - dramatic wrinkle formation"
        )
        self.pull_vertices = []
        
    def setup(self):
        """Set up tablecloth mesh"""
        # Large tablecloth (3m x 2m)
        resolution_x = 60
        resolution_y = 40
        width = 3.0
        height = 2.0
        
        # Generate vertices - start draped on table
        x = np.linspace(-width/2, width/2, resolution_x)
        y = np.linspace(-height/2, height/2, resolution_y)
        
        vertices = []
        for yi in range(resolution_y):
            for xi in range(resolution_x):
                # Slight drape at edges
                z = 1.0 - 0.1 * (abs(x[xi]/(width/2))**2 + abs(y[yi]/(height/2))**2)
                vertices.append([x[xi], y[yi], z])
        
        vertices = np.array(vertices, dtype=np.float32)
        
        # Generate triangles
        triangles = []
        for yi in range(resolution_y - 1):
            for xi in range(resolution_x - 1):
                i0 = yi * resolution_x + xi
                i1 = i0 + 1
                i2 = i0 + resolution_x
                i3 = i2 + 1
                
                triangles.append([i0, i2, i1])
                triangles.append([i1, i2, i3])
        
        triangles = np.array(triangles, dtype=np.int32)
        
        # Store for export/visualization
        self.rest_positions = vertices.copy()
        self.triangles = triangles
        
        # Material: Cotton (medium weight)
        material = create_cloth_material('cotton')
        
        # Initialize mesh
        self.mesh = abc.Mesh()
        self.mesh.initialize(vertices, triangles, material)
        
        # Initialize state
        self.state = abc.State()
        self.state.initialize(self.mesh)
        
        # Constraints
        self.constraints = abc.Constraints()
        
        # Table surface at z=0.9
        table_normal = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        self.constraints.add_wall(table_normal, 0.9, 0.01)
        
        # Ground floor at z=0
        ground_normal = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        self.constraints.add_wall(ground_normal, 0.0, 0.01)
        
        # Identify vertices to "pull" (right edge)
        for yi in range(resolution_y):
            idx = yi * resolution_x + (resolution_x - 1)  # Last column
            self.pull_vertices.append(idx)
        
        # Simulation parameters - balanced for stability and quality
        self.params = abc.SimParams()
        self.params.dt = 0.005  # 5ms timestep (more stable)
        self.params.beta_max = 0.2  # Lower beta for more stability
        self.params.min_newton_steps = 2
        self.params.max_newton_steps = 8
        self.params.pcg_tol = 1e-3  # Looser tolerance
        self.params.pcg_max_iters = 100
        self.params.contact_gap_max = 0.001
        self.params.wall_gap = 0.001
        self.params.enable_ccd = True
        
        print(f"Tablecloth: {len(vertices)} vertices, {len(triangles)} triangles")
        print(f"Pull vertices: {len(self.pull_vertices)} (right edge)")
        
    def run(self, num_frames=400, dt=None):
        """Override run to apply pull force"""
        # Setup if not already done
        if self.mesh is None:
            self.setup()
        
        if dt is None:
            dt = self.params.dt
        
        print(f"\n{'='*60}")
        print(f"Demo: {self.name}")
        print(f"{'='*60}")
        print(f"Description: {self.description}")
        print(f"Frames: {num_frames}, dt: {dt}s")
        print()
        
        # Collect initial frame
        self.frames.append(self.state.get_positions().copy())
        
        # Run simulation with pull force
        import time
        base_gravity = np.array([0.0, 0.0, -9.81], dtype=np.float32)
        
        print("Running simulation...")
        start_time = time.time()
        
        for frame in range(num_frames):
            # Apply gravity first
            self.state.apply_gravity(base_gravity, dt)
            
            # Pull force: Gentle horizontal pull on right edge
            # Very smooth ramp-up to avoid instability
            if frame < 150:
                # Extra smooth cubic ramp-up
                t = frame / 150.0
                pull_strength = 1.5 * t * t * (3.0 - 2.0 * t)  # Smoothstep
            else:
                pull_strength = 1.5
            
            # Apply pull as velocity adjustment (simpler, more stable)
            velocities = self.state.get_velocities()
            
            for idx in self.pull_vertices:
                # Directly add velocity in +X direction
                velocities[idx][0] += pull_strength * dt
            
            # Set modified velocities
            self.state.set_velocities(velocities)
            
            # Physics step
            step_start = time.time()
            abc.Integrator.step(self.mesh, self.state, self.constraints, self.params)
            step_time = (time.time() - step_start) * 1000
            
            # Store frame
            self.frames.append(self.state.get_positions().copy())
            self.stats.append({'frame': frame, 'step_time_ms': step_time})
            
            # Progress
            if (frame + 1) % 40 == 0:
                elapsed = time.time() - start_time
                fps = (frame + 1) / elapsed
                print(f"  Frame {frame+1}/{num_frames} | "
                      f"Step: {step_time:.1f}ms | FPS: {fps:.1f}")
        
        total_time = time.time() - start_time
        avg_fps = num_frames / total_time
        avg_step = np.mean([s['step_time_ms'] for s in self.stats])
        
        print(f"\n{'='*60}")
        print(f"Simulation complete!")
        print(f"Total time: {total_time:.1f}s")
        print(f"Average FPS: {avg_fps:.1f}")
        print(f"Average step time: {avg_step:.1f}ms")
        print(f"{'='*60}\n")
    
    def has_ground_plane(self):
        return True


if __name__ == '__main__':
    demo = TableclothPullDemo()
    demo.run(num_frames=400)
    
    # Export OBJ sequence
    demo.export_obj_sequence('output/tablecloth_pull')
    
    # Visualize
    try:
        demo.visualize(window_size=(1600, 900), fps=60)
    except Exception as e:
        print(f"Visualization failed: {e}")
        print("OBJ sequence exported to output/tablecloth_pull/")
