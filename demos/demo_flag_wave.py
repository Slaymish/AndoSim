#!/usr/bin/env python3
"""
Demo 1: Waving Flag
A dramatic cloth simulation showing a flag waving in the wind
Tests: Pin constraints, material dynamics, complex motion
"""

import numpy as np
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))

import ando_barrier_core as abc
from demo_framework import PhysicsDemo, create_grid_mesh, create_cloth_material


class WavingFlagDemo(PhysicsDemo):
    """Flag pinned on left edge, waving in simulated wind"""
    
    def __init__(self):
        super().__init__(
            name="Waving Flag",
            description="Cloth flag pinned on left edge with wind force simulation"
        )
        self.pin_indices = []
        self.wind_phase = 0
        
    def setup(self):
        """Set up flag mesh and constraints"""
        # Create rectangular flag (2:1 aspect ratio)
        resolution_x = 40
        resolution_y = 20
        width = 2.0
        height = 1.0
        
        # Generate vertices
        x = np.linspace(0, width, resolution_x)
        y = np.linspace(-height/2, height/2, resolution_y)
        
        vertices = []
        for yi in range(resolution_y):
            for xi in range(resolution_x):
                vertices.append([x[xi], y[yi], 0.5 + yi * 0.01])  # Slight wave initially
        
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
        
        # Material: Silk (light and flowing)
        material = create_cloth_material('silk')
        
        # Initialize mesh
        self.mesh = abc.Mesh()
        self.mesh.initialize(vertices, triangles, material)
        
        # Initialize state
        self.state = abc.State()
        self.state.initialize(self.mesh)
        
        # Constraints
        self.constraints = abc.Constraints()
        
        # Pin left edge vertices (flagpole)
        for yi in range(resolution_y):
            idx = yi * resolution_x  # First column
            pin_pos = vertices[idx]
            self.constraints.add_pin(idx, pin_pos)
            self.pin_indices.append(idx)
        
        # Ground plane below
        ground_normal = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        self.constraints.add_wall(ground_normal, -0.5, 0.01)
        
        # Simulation parameters
        self.params = abc.SimParams()
        self.params.dt = 0.005  # 5ms timestep for smooth motion
        self.params.beta_max = 0.25
        self.params.min_newton_steps = 2
        self.params.max_newton_steps = 8
        self.params.pcg_tol = 1e-3
        self.params.pcg_max_iters = 100
        self.params.contact_gap_max = 0.001
        self.params.wall_gap = 0.001
        self.params.enable_ccd = True
        
        print(f"Flag mesh: {len(vertices)} vertices, {len(triangles)} triangles")
        print(f"Pinned: {len(self.pin_indices)} vertices (left edge)")
        
    def run(self, num_frames=300, dt=None):
        """Override run to add wind forces"""
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
        
        # Run simulation with wind
        import time
        base_gravity = np.array([0.0, 0.0, -9.81], dtype=np.float32)
        
        print("Running simulation...")
        start_time = time.time()
        
        for frame in range(num_frames):
            # Wind force: periodic in X direction with turbulence
            wind_strength = 8.0 * (0.7 + 0.3 * np.sin(frame * 0.1))
            wind_turbulence = 2.0 * np.sin(frame * 0.3 + np.sin(frame * 0.05))
            wind = np.array([wind_strength + wind_turbulence, 0.0, 0.0], dtype=np.float32)
            
            # Combined forces
            forces = base_gravity + wind
            
            # Apply forces
            self.state.apply_gravity(forces, dt)
            
            # Physics step
            step_start = time.time()
            abc.Integrator.step(self.mesh, self.state, self.constraints, self.params)
            step_time = (time.time() - step_start) * 1000
            
            # Store frame
            self.frames.append(self.state.get_positions().copy())
            self.stats.append({'frame': frame, 'step_time_ms': step_time})
            
            # Progress
            if (frame + 1) % 30 == 0:
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
    
    def get_pin_positions(self):
        """Return positions of pinned vertices"""
        if self.frames:
            return [self.frames[0][i] for i in self.pin_indices]
        return []
    
    def has_ground_plane(self):
        return True


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Waving Flag Demo')
    parser.add_argument('--cached', action='store_true', 
                        help='Load cached simulation from output/flag_wave instead of running simulation')
    parser.add_argument('--frames', type=int, default=300,
                        help='Number of frames to simulate (default: 300)')
    parser.add_argument('--output', type=str, default='output/flag_wave',
                        help='Output directory for OBJ files (default: output/flag_wave)')
    args = parser.parse_args()
    
    demo = WavingFlagDemo()
    
    if args.cached:
        # Load from cached OBJ files
        demo.load_cached(args.output)
    else:
        # Run simulation
        demo.run(num_frames=args.frames)
        
        # Export OBJ sequence
        demo.export_obj_sequence(args.output)
    
    # Visualize if PyVista available
    try:
        demo.visualize(window_size=(1600, 900), fps=60)
    except Exception as e:
        print(f"Visualization failed: {e}")
        if not args.cached:
            print(f"OBJ sequence exported to {args.output}/")

