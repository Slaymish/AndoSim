#!/usr/bin/env python3
"""
Demo 3: Cascading Curtains
Multiple cloth layers stacking and interacting
Tests: Self-collision, multi-body dynamics, complex contact scenarios
"""

import numpy as np
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))

import ando_barrier_core as abc
from demo_framework import PhysicsDemo, create_cloth_material


class CascadingCurtainsDemo(PhysicsDemo):
    """Three curtain panels dropping and stacking"""
    
    def __init__(self):
        super().__init__(
            name="Cascading Curtains",
            description="Three cloth curtains falling and draping - tests multi-layer contact"
        )
        self.pin_indices = []
        
    def setup(self):
        """Set up three curtain panels at different heights"""
        resolution_x = 25
        resolution_y = 35
        width = 1.2
        height = 1.8
        
        # We'll create one combined mesh with three separated panels
        all_vertices = []
        all_triangles = []
        vertex_offset = 0
        
        # Generate three curtain panels
        for panel_idx in range(3):
            x_offset = (panel_idx - 1) * (width * 0.4)  # Offset horizontally
            z_offset = 2.5 - panel_idx * 0.3  # Stagger heights
            
            # Generate vertices for this panel
            x = np.linspace(-width/2, width/2, resolution_x) + x_offset
            y = np.linspace(-height/2, height/2, resolution_y)
            
            panel_vertices = []
            for yi in range(resolution_y):
                for xi in range(resolution_x):
                    # Add some initial waviness
                    z = z_offset + 0.05 * np.sin(xi * 0.5) * np.cos(yi * 0.3)
                    panel_vertices.append([x[xi], y[yi], z])
            
            panel_vertices = np.array(panel_vertices, dtype=np.float32)
            
            # Generate triangles for this panel
            panel_triangles = []
            for yi in range(resolution_y - 1):
                for xi in range(resolution_x - 1):
                    i0 = yi * resolution_x + xi + vertex_offset
                    i1 = i0 + 1
                    i2 = i0 + resolution_x
                    i3 = i2 + 1
                    
                    panel_triangles.append([i0, i2, i1])
                    panel_triangles.append([i1, i2, i3])
            
            # Pin top edge of each panel
            for xi in range(resolution_x):
                pin_idx = vertex_offset + xi  # Top row
                self.pin_indices.append(pin_idx)
            
            all_vertices.extend(panel_vertices)
            all_triangles.extend(panel_triangles)
            
            vertex_offset += len(panel_vertices)
        
        vertices = np.array(all_vertices, dtype=np.float32)
        triangles = np.array(all_triangles, dtype=np.int32)
        
        # Store for export/visualization
        self.rest_positions = vertices.copy()
        self.triangles = triangles
        
        # Material: Silk (light and flowing)
        material = create_cloth_material('silk')
        material.density = 250  # Even lighter for dramatic draping
        
        # Initialize mesh
        self.mesh = abc.Mesh()
        self.mesh.initialize(vertices, triangles, material)
        
        # Initialize state
        self.state = abc.State()
        self.state.initialize(self.mesh)
        
        # Constraints
        self.constraints = abc.Constraints()
        
        # Pin top edges
        for pin_idx in self.pin_indices:
            pin_pos = vertices[pin_idx]
            self.constraints.add_pin(pin_idx, pin_pos)
        
        # Ground plane
        ground_normal = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        self.constraints.add_wall(ground_normal, 0.0, 0.01)
        
        # Simulation parameters
        self.params = abc.SimParams()
        self.params.dt = 0.004  # 4ms timestep
        self.params.beta_max = 0.25
        self.params.min_newton_steps = 3
        self.params.max_newton_steps = 10
        self.params.pcg_tol = 1e-3
        self.params.pcg_max_iters = 120
        self.params.contact_gap_max = 0.002  # Slightly larger for multi-layer
        self.params.wall_gap = 0.002
        self.params.enable_ccd = True
        
        print(f"Curtains: 3 panels × {resolution_x}×{resolution_y} vertices")
        print(f"Total: {len(vertices)} vertices, {len(triangles)} triangles")
        print(f"Pinned: {len(self.pin_indices)} vertices (top edges)")
    
    def get_pin_positions(self):
        """Return positions of pinned vertices"""
        if self.frames:
            return [self.frames[0][i] for i in self.pin_indices]
        return []
    
    def has_ground_plane(self):
        return True


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Cascading Curtains Demo')
    parser.add_argument('--cached', action='store_true',
                        help='Load cached simulation from output directory instead of running simulation')
    parser.add_argument('--frames', type=int, default=500,
                        help='Number of frames to simulate (default: 500)')
    parser.add_argument('--dt', type=float, default=0.004,
                        help='Time step in seconds (default: 0.004)')
    parser.add_argument('--output', type=str, default='output/cascading_curtains',
                        help='Output directory for OBJ files (default: output/cascading_curtains)')
    args = parser.parse_args()
    
    demo = CascadingCurtainsDemo()
    
    if args.cached:
        # Load from cached OBJ files
        demo.load_cached(args.output)
    else:
        # Run simulation
        demo.run(num_frames=args.frames, dt=args.dt)
        
        # Export OBJ sequence
        demo.export_obj_sequence(args.output)
    
    # Visualize
    try:
        demo.visualize(window_size=(1600, 900), fps=60)
    except Exception as e:
        print(f"Visualization failed: {e}")
        if not args.cached:
            print(f"OBJ sequence exported to {args.output}/")

