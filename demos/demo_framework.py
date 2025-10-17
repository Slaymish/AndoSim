"""
High-quality demo framework using PyVista for 3D visualization
Provides interactive playback with better rendering than matplotlib
"""

import numpy as np
import sys
import os

# Add build directory to path for module import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))

try:
    import pyvista as pv
    HAS_PYVISTA = True
except ImportError:
    print("PyVista not installed. Install with: pip install pyvista")
    HAS_PYVISTA = False

import ando_barrier_core as abc


class PhysicsDemo:
    """Base class for physics demonstrations"""
    
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.mesh = None
        self.state = None
        self.constraints = None
        self.params = None
        self.frames = []
        self.stats = []
        self.triangles = None  # Store triangles for export
        self.rest_positions = None  # Store initial positions
        
    def setup(self):
        """Override: Set up mesh, materials, constraints"""
        raise NotImplementedError
        
    def run(self, num_frames=200, dt=0.01):
        """Run simulation and collect frames"""
        print(f"\n{'='*60}")
        print(f"Demo: {self.name}")
        print(f"{'='*60}")
        print(f"Description: {self.description}")
        print(f"Frames: {num_frames}, dt: {dt}s")
        print()
        
        # Setup simulation
        self.setup()
        self.params.dt = dt
        
        # Collect initial frame
        self.frames.append(self.state.get_positions().copy())
        
        # Run simulation
        import time
        gravity = np.array([0.0, 0.0, -9.81], dtype=np.float32)
        
        print("Running simulation...")
        start_time = time.time()
        
        for frame in range(num_frames):
            # Apply gravity
            self.state.apply_gravity(gravity, dt)
            
            # Physics step
            step_start = time.time()
            abc.Integrator.step(self.mesh, self.state, self.constraints, self.params)
            step_time = (time.time() - step_start) * 1000
            
            # Store frame
            self.frames.append(self.state.get_positions().copy())
            self.stats.append({
                'frame': frame,
                'step_time_ms': step_time,
            })
            
            # Progress
            if (frame + 1) % 20 == 0:
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
        
    def visualize(self, window_size=(1280, 720), fps=30):
        """Visualize simulation using PyVista"""
        if not HAS_PYVISTA:
            print("PyVista not available. Install with: pip install pyvista")
            return
            
        if not self.frames:
            print("No frames to visualize. Run simulation first.")
            return
        
        print(f"Visualizing {len(self.frames)} frames...")
        print("Controls:")
        print("  - Space: Play/Pause")
        print("  - Left/Right arrows: Step backward/forward")
        print("  - Q: Quit")
        print()
        
        # Create plotter
        plotter = pv.Plotter(window_size=window_size)
        plotter.set_background('white')
        plotter.add_axes()
        
        # Get mesh topology (from stored data)
        if self.rest_positions is None or self.triangles is None:
            print("ERROR: Mesh topology not stored. Call setup() first or store triangles in subclass.")
            return
        
        vertices = self.rest_positions
        triangles = self.triangles
        
        # Create PyVista mesh
        faces = np.hstack([np.full((len(triangles), 1), 3), triangles]).astype(int)
        mesh = pv.PolyData(vertices, faces)
        
        # Add mesh actor with nice shading
        actor = plotter.add_mesh(
            mesh,
            color='lightblue',
            show_edges=True,
            edge_color='gray',
            lighting=True,
            smooth_shading=True,
            specular=0.5,
            specular_power=15,
        )
        
        # Add ground plane visualization
        if self.has_ground_plane():
            ground = pv.Plane(center=(0, 0, 0), direction=(0, 0, 1), 
                            i_size=3, j_size=3)
            plotter.add_mesh(ground, color='tan', opacity=0.3)
        
        # Add pin indicators
        pin_positions = self.get_pin_positions()
        if pin_positions:
            pins = pv.PolyData(pin_positions)
            plotter.add_mesh(pins, color='blue', point_size=10, 
                           render_points_as_spheres=True)
        
        # Camera setup
        plotter.camera_position = 'iso'
        plotter.camera.zoom(1.2)
        
        # Animation state
        anim_state = {
            'frame': 0,
            'playing': False,
            'last_update': 0,
        }
        
        frame_delay = 1.0 / fps
        
        def update_frame(frame_idx):
            """Update mesh to specific frame"""
            positions = self.frames[frame_idx]
            mesh.points = positions
            mesh.compute_normals(inplace=True)
            # Only update/render if interactor is initialized
            if plotter.iren and plotter.iren.initialized:
                plotter.update()
                plotter.render()
        
        def on_timer():
            """Timer callback for animation"""
            import time
            if anim_state['playing']:
                current_time = time.time()
                if current_time - anim_state['last_update'] >= frame_delay:
                    anim_state['frame'] = (anim_state['frame'] + 1) % len(self.frames)
                    update_frame(anim_state['frame'])
                    anim_state['last_update'] = current_time
                    plotter.add_text(
                        f"Frame {anim_state['frame']}/{len(self.frames)-1} | "
                        f"{'Playing' if anim_state['playing'] else 'Paused'}",
                        position='upper_left',
                        font_size=12,
                        name='status'
                    )
        
        # Set up timer callback
        # PyVista passes step number as argument, so lambda must accept it
        plotter.add_timer_event(max_steps=999999, duration=int(frame_delay * 1000), 
                               callback=lambda step: on_timer())
        
        # Key event callbacks - define functions with closures
        def on_space():
            """Toggle play/pause"""
            try:
                anim_state['playing'] = not anim_state['playing']
                status_text = 'Playing' if anim_state['playing'] else 'Paused'
                print(f"{status_text}")
                plotter.add_text(
                    f"Frame {anim_state['frame']}/{len(self.frames)-1} | {status_text}",
                    position='upper_left',
                    font_size=12,
                    name='status'
                )
            except Exception as e:
                print(f"Error in on_space: {e}")
                import traceback
                traceback.print_exc()
        
        def on_right():
            """Step forward"""
            try:
                anim_state['frame'] = min(anim_state['frame'] + 1, len(self.frames) - 1)
                update_frame(anim_state['frame'])
                print(f"Frame {anim_state['frame']}/{len(self.frames)-1}")
                plotter.add_text(
                    f"Frame {anim_state['frame']}/{len(self.frames)-1} | Paused",
                    position='upper_left',
                    font_size=12,
                    name='status'
                )
            except Exception as e:
                print(f"Error in on_right: {e}")
                import traceback
                traceback.print_exc()
        
        def on_left():
            """Step backward"""
            try:
                anim_state['frame'] = max(anim_state['frame'] - 1, 0)
                update_frame(anim_state['frame'])
                print(f"Frame {anim_state['frame']}/{len(self.frames)-1}")
                plotter.add_text(
                    f"Frame {anim_state['frame']}/{len(self.frames)-1} | Paused",
                    position='upper_left',
                    font_size=12,
                    name='status'
                )
            except Exception as e:
                print(f"Error in on_left: {e}")
                import traceback
                traceback.print_exc()
        
        # Register key events - try different key name variations
        # PyVista might be case-sensitive or use different names
        print("\nKeyboard controls:")
        print("  space - Toggle play/pause")
        print("  Right - Step forward")
        print("  Left - Step backward")
        print("  q - Quit\n")
        
        plotter.add_key_event('space', on_space)  # Try lowercase space
        plotter.add_key_event('Right', on_right)
        plotter.add_key_event('Left', on_left)
        
        # Initial setup - just set geometry, don't update/render yet
        positions = self.frames[0]
        mesh.points = positions
        mesh.compute_normals(inplace=True)
        
        # Add initial status text
        plotter.add_text(
            f"Frame 0/{len(self.frames)-1} | Paused",
            position='upper_left',
            font_size=12,
            name='status'
        )
        
        # Show (this initializes the interactor)
        plotter.show()
    
    def has_ground_plane(self):
        """Check if demo has ground plane constraint"""
        # Check if constraints has walls
        # This is a heuristic - you might want to track this explicitly
        return True  # Most demos have ground plane
    
    def get_pin_positions(self):
        """Get positions of pinned vertices"""
        # Override in subclasses if you track pins
        return []
    
    def export_obj_sequence(self, output_dir):
        """Export frames as OBJ sequence (for compatibility)"""
        if self.triangles is None:
            print("ERROR: Triangles not stored. Store triangles in setup() before exporting.")
            return
        
        os.makedirs(output_dir, exist_ok=True)
        
        triangles = self.triangles
        
        for i, positions in enumerate(self.frames):
            filename = os.path.join(output_dir, f"frame_{i:04d}.obj")
            with open(filename, 'w') as f:
                # Vertices
                for v in positions:
                    f.write(f"v {v[0]} {v[1]} {v[2]}\n")
                # Faces (1-indexed)
                for tri in triangles:
                    f.write(f"f {tri[0]+1} {tri[1]+1} {tri[2]+1}\n")
        
        print(f"Exported {len(self.frames)} frames to {output_dir}/")


def create_grid_mesh(resolution=20, size=1.0):
    """Helper: Create a grid mesh"""
    x = np.linspace(-size/2, size/2, resolution)
    y = np.linspace(-size/2, size/2, resolution)
    
    vertices = []
    for yi in range(resolution):
        for xi in range(resolution):
            vertices.append([x[xi], y[yi], 0.0])
    
    vertices = np.array(vertices, dtype=np.float32)
    
    # Triangles
    triangles = []
    for yi in range(resolution - 1):
        for xi in range(resolution - 1):
            i0 = yi * resolution + xi
            i1 = i0 + 1
            i2 = i0 + resolution
            i3 = i2 + 1
            
            triangles.append([i0, i2, i1])
            triangles.append([i1, i2, i3])
    
    triangles = np.array(triangles, dtype=np.int32)
    
    return vertices, triangles


def create_cloth_material(style='default'):
    """Helper: Create material presets"""
    material = abc.Material()
    
    if style == 'silk':
        material.youngs_modulus = 5e5
        material.poisson_ratio = 0.3
        material.density = 200
        material.thickness = 0.0003
    elif style == 'cotton':
        material.youngs_modulus = 1e6
        material.poisson_ratio = 0.3
        material.density = 300
        material.thickness = 0.0005
    elif style == 'leather':
        material.youngs_modulus = 5e6
        material.poisson_ratio = 0.35
        material.density = 800
        material.thickness = 0.002
    elif style == 'rubber':
        material.youngs_modulus = 1e5
        material.poisson_ratio = 0.45
        material.density = 900
        material.thickness = 0.002
    else:  # default
        material.youngs_modulus = 1e6
        material.poisson_ratio = 0.3
        material.density = 1000
        material.thickness = 0.001
    
    return material
