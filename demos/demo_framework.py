"""
High-quality demo framework using PyVista for 3D visualization
Provides interactive playback with better rendering than matplotlib
"""

import numpy as np
import sys
import os
import time

# Add build directory to path for module import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))

HAS_PYVISTA = False
HAS_MATPLOTLIB = False

try:
    import pyvista as pv
    HAS_PYVISTA = True
except ImportError:
    print("PyVista not installed. Install with: pip install pyvista")

try:
    import matplotlib.pyplot as plt
    from matplotlib import animation as mpl_animation
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    HAS_MATPLOTLIB = True
except ImportError:
    print("Matplotlib not installed. Install with: pip install matplotlib")

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
        """Visualize simulation using PyVista if available, otherwise Matplotlib."""
        if not self.frames:
            print("No frames to visualize. Run simulation first.")
            return

        if HAS_PYVISTA:
            self._visualize_with_pyvista(window_size, fps)
        elif HAS_MATPLOTLIB:
            self._visualize_with_matplotlib(fps)
        else:
            print("No visualization backend available. Install PyVista or Matplotlib.")

    def _visualize_with_pyvista(self, window_size, fps):
        """Interactive visualization using PyVista."""
        print(f"Visualizing {len(self.frames)} frames with PyVista...")
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
        
        def set_status():
            status_text = f"Frame {anim_state['frame']}/{len(self.frames)-1} | {'Playing' if anim_state['playing'] else 'Paused'}"
            plotter.add_text(
                status_text,
                position='upper_left',
                font_size=12,
                name='status'
            )

        def update_frame(frame_idx, *, render=True):
            """Update mesh to specific frame"""
            positions = self.frames[frame_idx]
            np_positions = np.asarray(positions)
            current_points = mesh.points
            if current_points.shape == np_positions.shape:
                current_points[:] = np_positions
            else:
                mesh.points = np_positions
            mesh.compute_normals(inplace=True)
            mesh.modified()
            if render and plotter.iren and plotter.iren.initialized:
                plotter.render()
            set_status()
        
        def animation_callback():
            """Repeated callback to advance frames when playing."""
            if not anim_state['playing']:
                return
            current_time = time.time()
            if current_time - anim_state['last_update'] >= frame_delay:
                anim_state['frame'] = (anim_state['frame'] + 1) % len(self.frames)
                anim_state['last_update'] = current_time
                update_frame(anim_state['frame'])
        
        # Set up timer callback
        # PyVista passes step number as argument, so lambda must accept it
        def timer_callback(step):
            animation_callback()

        plotter.add_timer_event(
            max_steps=1_000_000,
            duration=max(int(frame_delay * 1000), 1),
            callback=timer_callback,
        )
        
        # Key event callbacks - define functions with closures
        def on_space():
            """Toggle play/pause"""
            try:
                anim_state['playing'] = not anim_state['playing']
                anim_state['last_update'] = time.time()
                status_text = 'Playing' if anim_state['playing'] else 'Paused'
                print(status_text)
                set_status()
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
                anim_state['playing'] = False
                anim_state['last_update'] = time.time()
                set_status()
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
                anim_state['playing'] = False
                anim_state['last_update'] = time.time()
                set_status()
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
        
        for key in ('space', 'Space', ' ', 'Return'):
            plotter.add_key_event(key, on_space)
        for key in ('Right', 'right', 'd'):
            plotter.add_key_event(key, on_right)
        for key in ('Left', 'left', 'a'):
            plotter.add_key_event(key, on_left)
        for key in ('q', 'Q', 'Escape'):
            plotter.add_key_event(key, lambda: plotter.close())
        
        # Initial setup - just set geometry, don't update/render yet
        positions = self.frames[0]
        mesh.points = positions
        mesh.compute_normals(inplace=True)
        
        # Add initial status text
        set_status()
        anim_state['last_update'] = time.time()
        
        # Show (this initializes the interactor)
        plotter.show()

    def _visualize_with_matplotlib(self, fps):
        """Fallback visualization using Matplotlib with keyboard controls."""
        print(f"Visualizing {len(self.frames)} frames with Matplotlib...")
        print("Controls:")
        print("  - Space: Play/Pause")
        print("  - Left/Right arrows: Step backward/forward")
        print("  - Q/Escape: Quit")
        print()

        frames = [np.asarray(frame) for frame in self.frames]
        triangles = np.asarray(self.triangles, dtype=int)

        fig = plt.figure(figsize=(10, 7))
        ax = fig.add_subplot(111, projection='3d')
        try:
            fig.canvas.manager.set_window_title(f"AndoSim Demo - {self.name}")
        except Exception:
            pass  # Backend may not support setting window title

        # Build triangle vertex list for Poly3DCollection
        def make_faces(points):
            return [points[tri] for tri in triangles]

        poly = Poly3DCollection(make_faces(frames[0]), facecolors=(0.6, 0.8, 1.0, 0.9),
                                edgecolors='gray', linewidths=0.5)
        ax.add_collection3d(poly)

        # Plot pins if present
        pin_positions = self.get_pin_positions()
        pin_scatter = None
        if pin_positions:
            pin_positions = np.asarray(pin_positions)
            pin_scatter = ax.scatter(pin_positions[:, 0], pin_positions[:, 1],
                                     pin_positions[:, 2], color='blue', s=30, label='Pins')

        # Auto scale axes
        all_points = np.vstack(frames)
        min_bounds = all_points.min(axis=0)
        max_bounds = all_points.max(axis=0)
        center = (max_bounds + min_bounds) / 2.0
        extent = (max_bounds - min_bounds).max() * 0.6
        extent = max(extent, 1e-3)

        ax.set_xlim(center[0] - extent, center[0] + extent)
        ax.set_ylim(center[1] - extent, center[1] + extent)
        ax.set_zlim(center[2] - extent, center[2] + extent)
        ax.set_box_aspect([1, 1, 1])
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        ax.view_init(elev=25, azim=-60)

        status_text = ax.text2D(0.02, 0.95, "Frame 0 | Paused", transform=ax.transAxes)

        state = {
            'frame': 0,
            'playing': False,
        }

        interval_ms = max(int(1000 / max(fps, 1)), 1)
        timer = fig.canvas.new_timer(interval=interval_ms)

        def update_frame(frame_idx):
            state['frame'] = frame_idx
            positions = frames[frame_idx]
            poly.set_verts(make_faces(positions))
            status_text.set_text(
                f"Frame {frame_idx}/{len(frames) - 1} | {'Playing' if state['playing'] else 'Paused'}"
            )
            fig.canvas.draw_idle()

        def on_timer():
            if state['playing']:
                update_frame((state['frame'] + 1) % len(frames))

        def on_key(event):
            key = event.key.lower()
            if key == ' ':
                state['playing'] = not state['playing']
                update_frame(state['frame'])
            elif key == 'right':
                state['playing'] = False
                update_frame(min(state['frame'] + 1, len(frames) - 1))
            elif key == 'left':
                state['playing'] = False
                update_frame(max(state['frame'] - 1, 0))
            elif key in ('q', 'escape'):
                plt.close(fig)

        timer.add_callback(on_timer)
        timer.start()
        fig.canvas.mpl_connect('key_press_event', on_key)
        update_frame(0)

        plt.tight_layout()
        plt.show()
    
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
