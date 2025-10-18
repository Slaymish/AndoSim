#!/usr/bin/env python3
"""
Quick test to verify PyVista interaction works
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'demos'))

# Test with a smaller, faster demo
from demo_framework import PhysicsDemo, create_grid_mesh, create_cloth_material
import numpy as np

sys.path.insert(0, 'build')
import ando_barrier_core as abc

class QuickTestDemo(PhysicsDemo):
    """Minimal demo for testing visualization"""
    
    def __init__(self):
        super().__init__(
            name="Quick Test",
            description="Small mesh for testing PyVista interaction"
        )
        
    def setup(self):
        """Set up a small 5x5 grid"""
        vertices, triangles = create_grid_mesh(resolution=5, size=0.5)
        
        # Lift it up slightly
        vertices[:, 2] = 0.3
        
        self.rest_positions = vertices.copy()
        self.triangles = triangles
        
        material = create_cloth_material('default')
        
        self.mesh = abc.Mesh()
        self.mesh.initialize(vertices, triangles, material)
        
        self.state = abc.State()
        self.state.initialize(self.mesh)
        
        self.constraints = abc.Constraints()
        
        # Pin two corners
        self.constraints.add_pin(0, vertices[0])
        self.constraints.add_pin(4, vertices[4])
        
        # Ground
        ground_normal = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        self.constraints.add_wall(ground_normal, 0.0, 0.01)
        
        self.params = abc.SimParams()
        self.params.dt = 0.01
        
        print(f"Test mesh: {len(vertices)} vertices, {len(triangles)} triangles")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Quick PyVista Test')
    parser.add_argument('--cached', action='store_true',
                        help='Load cached simulation from output/quick_test instead of running simulation')
    parser.add_argument('--frames', type=int, default=50,
                        help='Number of frames to simulate (default: 50)')
    parser.add_argument('--output', type=str, default='output/quick_test',
                        help='Output directory for OBJ files (default: output/quick_test)')
    args = parser.parse_args()
    
    demo = QuickTestDemo()
    
    if args.cached:
        # Load from cached OBJ files
        demo.load_cached(args.output)
    else:
        # Run simulation
        demo.run(num_frames=args.frames)
        
        # Export for caching
        demo.export_obj_sequence(args.output)
    
    print("\n" + "="*60)
    print("Opening PyVista window...")
    print("Try these controls:")
    print("  - Left mouse drag: Orbit camera (should work now!)")
    print("  - Space: Toggle play/pause")
    print("  - Right arrow: Step forward")
    print("  - Left arrow: Step backward")
    print("="*60 + "\n")
    
    try:
        demo.visualize(window_size=(800, 600), fps=30)
    except Exception as e:
        print(f"Visualization failed: {e}")
        import traceback
        traceback.print_exc()

