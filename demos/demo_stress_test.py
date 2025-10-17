#!/usr/bin/env python3
"""
Demo 4: Stress Test - High Resolution Cloth Drop
Tests solver stability and performance limits
"""

import numpy as np
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))

import ando_barrier_core as abc
from demo_framework import PhysicsDemo, create_cloth_material


class StressTestDemo(PhysicsDemo):
    """High-resolution cloth to test performance limits"""
    
    def __init__(self, resolution=50):
        self.resolution = resolution
        super().__init__(
            name=f"Stress Test ({resolution}×{resolution})",
            description=f"High-resolution cloth drop with {resolution*resolution} vertices"
        )
        self.pin_indices = []
        
    def setup(self):
        """Set up high-resolution cloth mesh"""
        res = self.resolution
        size = 2.0
        
        # Generate high-res grid
        x = np.linspace(-size/2, size/2, res)
        y = np.linspace(-size/2, size/2, res)
        
        vertices = []
        for yi in range(res):
            for xi in range(res):
                # Start elevated with ripples
                z = 2.0 + 0.1 * np.sin(xi * 0.3) * np.cos(yi * 0.3)
                vertices.append([x[xi], y[yi], z])
        
        vertices = np.array(vertices, dtype=np.float32)
        
        # Generate triangles
        triangles = []
        for yi in range(res - 1):
            for xi in range(res - 1):
                i0 = yi * res + xi
                i1 = i0 + 1
                i2 = i0 + res
                i3 = i2 + 1
                
                triangles.append([i0, i2, i1])
                triangles.append([i1, i2, i3])
        
        triangles = np.array(triangles, dtype=np.int32)
        
        # Store for export/visualization
        self.rest_positions = vertices.copy()
        self.triangles = triangles
        
        # Material: Cotton
        material = create_cloth_material('cotton')
        
        # Initialize mesh
        self.mesh = abc.Mesh()
        self.mesh.initialize(vertices, triangles, material)
        
        # Initialize state
        self.state = abc.State()
        self.state.initialize(self.mesh)
        
        # Constraints
        self.constraints = abc.Constraints()
        
        # Pin four corners
        corners = [
            0,                    # Top-left
            res - 1,              # Top-right
            res * (res - 1),      # Bottom-left
            res * res - 1         # Bottom-right
        ]
        
        for corner_idx in corners:
            pin_pos = vertices[corner_idx]
            self.constraints.add_pin(corner_idx, pin_pos)
            self.pin_indices.append(corner_idx)
        
        # Ground plane
        ground_normal = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        self.constraints.add_wall(ground_normal, 0.0, 0.01)
        
        # Simulation parameters - optimized for performance
        self.params = abc.SimParams()
        self.params.dt = 0.008  # 8ms timestep for speed
        self.params.beta_max = 0.2
        self.params.min_newton_steps = 2
        self.params.max_newton_steps = 6
        self.params.pcg_tol = 2e-3  # Relaxed tolerance
        self.params.pcg_max_iters = 80
        self.params.contact_gap_max = 0.002
        self.params.wall_gap = 0.002
        self.params.enable_ccd = True
        
        total_triangles = len(triangles)
        print(f"High-res mesh: {len(vertices)} vertices ({res}×{res})")
        print(f"Triangles: {total_triangles}")
        print(f"Pinned: {len(self.pin_indices)} corners")
        print(f"Memory estimate: ~{(len(vertices) * 3 * 8 + total_triangles * 3 * 4) / 1024:.1f} KB")
    
    def get_pin_positions(self):
        """Return positions of pinned vertices"""
        if self.frames:
            return [self.frames[0][i] for i in self.pin_indices]
        return []
    
    def has_ground_plane(self):
        return True


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Stress test with configurable resolution')
    parser.add_argument('--resolution', type=int, default=50,
                       help='Mesh resolution (default: 50×50 = 2500 vertices)')
    parser.add_argument('--frames', type=int, default=200,
                       help='Number of frames to simulate (default: 200)')
    parser.add_argument('--no-viz', action='store_true',
                       help='Skip visualization (export only)')
    
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print("STRESS TEST")
    print(f"Resolution: {args.resolution}×{args.resolution} = {args.resolution**2} vertices")
    print(f"Estimated triangles: {(args.resolution-1)**2 * 2}")
    print(f"{'='*60}\n")
    
    demo = StressTestDemo(resolution=args.resolution)
    demo.run(num_frames=args.frames)
    
    # Always export
    demo.export_obj_sequence(f'output/stress_test_{args.resolution}x{args.resolution}')
    
    # Visualize unless disabled
    if not args.no_viz:
        try:
            demo.visualize(window_size=(1600, 900), fps=60)
        except Exception as e:
            print(f"Visualization failed: {e}")
            print(f"OBJ sequence exported to output/stress_test_{args.resolution}x{args.resolution}/")
    else:
        print("Visualization skipped (--no-viz)")
