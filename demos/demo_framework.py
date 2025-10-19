"""
High-quality demo framework using PyVista for 3D visualization
Provides interactive playback with better rendering than matplotlib
"""

import numpy as np
import sys
import os
import time

# Ensure PyVista runs in interactive, on-screen mode even if global theme defaults differ
os.environ.setdefault("PYVISTA_INTERACTIVE", "1")
os.environ.setdefault("PYVISTA_OFF_SCREEN", "0")

# Add build directory to path for module import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))

HAS_PYVISTA = False
HAS_MATPLOTLIB = False

try:
    import pyvista as pv
    # Override global defaults that disable interaction in newer PyVista releases
    pv.OFF_SCREEN = False
    pv.BUILDING_GALLERY = False
    pv.global_theme.interactive = True
    if hasattr(pv.global_theme, "notebook"):
        pv.global_theme.notebook = False
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
    
    def load_cached(self, cache_dir):
        """Load cached simulation from OBJ sequence"""
        import glob
        
        if not os.path.exists(cache_dir):
            raise FileNotFoundError(f"Cache directory not found: {cache_dir}")
        
        # Find all OBJ files
        obj_files = sorted(glob.glob(os.path.join(cache_dir, "frame_*.obj")))
        
        if not obj_files:
            raise FileNotFoundError(f"No OBJ files found in {cache_dir}")
        
        print(f"\n{'='*60}")
        print(f"Demo: {self.name}")
        print(f"{'='*60}")
        print(f"Loading cached simulation from: {cache_dir}")
        print(f"Found {len(obj_files)} frames")
        print()
        
        # Load first frame to get topology
        vertices, triangles = self._load_obj(obj_files[0])
        self.rest_positions = vertices
        self.triangles = triangles
        
        # Load all frames
        print("Loading frames...")
        for i, obj_file in enumerate(obj_files):
            verts, _ = self._load_obj(obj_file)
            self.frames.append(verts)
            
            if (i + 1) % 50 == 0:
                print(f"  Loaded {i+1}/{len(obj_files)} frames")
        
        print(f"\n{'='*60}")
        print(f"Cache loaded successfully!")
        print(f"Frames: {len(self.frames)}")
        print(f"Vertices: {len(self.rest_positions)}")
        print(f"Triangles: {len(self.triangles)}")
        print(f"{'='*60}\n")
    
    def _load_obj(self, filepath):
        """Load vertices and faces from OBJ file"""
        vertices = []
        faces = []
        
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('v '):
                    parts = line.split()
                    vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
                elif line.startswith('f '):
                    parts = line.split()
                    # OBJ faces are 1-indexed, convert to 0-indexed
                    face = [int(p.split('/')[0]) - 1 for p in parts[1:]]
                    faces.append(face)
        
        return np.array(vertices, dtype=np.float32), np.array(faces, dtype=np.int32)
        
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
        # Explicitly enable interactive mode; recent PyVista themes default to non-interactive
        plotter.theme.interactive = True
        plotter.enable_trackball_style()
        iren_enabled = False
        iren_initialized = False
        iren = getattr(plotter, "iren", None)
        vtk_iren = getattr(iren, "interactor", None) if iren is not None else None
        try:
            if iren is not None and hasattr(iren, "initialize"):
                iren.initialize()
                iren_initialized = True
            if vtk_iren is not None:
                if hasattr(vtk_iren, "Initialize"):
                    vtk_iren.Initialize()
                if hasattr(vtk_iren, "Enable"):
                    vtk_iren.Enable()
                if hasattr(vtk_iren, "GetEnabled"):
                    iren_enabled = bool(vtk_iren.GetEnabled())
        except Exception as exc:
            print(f"PyVista warning: failed to initialize interactor ({exc})")
        # Verbose debug hooks to track interaction events
        if vtk_iren is not None:
            def _debug_key_event(obj, evt):
                try:
                    key_sym = vtk_iren.GetKeySym()
                except Exception:
                    key_sym = str(evt)
                print(f"[PyVista] KeyPressEvent: {key_sym}")
            def _debug_start_interaction(obj, evt):
                print("[PyVista] StartInteractionEvent triggered")
            try:
                iren.add_observer('KeyPressEvent', _debug_key_event)
                iren.add_observer('StartInteractionEvent', _debug_start_interaction)
            except Exception as exc:
                print(f"PyVista warning: failed to add debug observers ({exc})")
        # Helpful diagnostics (printed once) so users can confirm interactivity is enabled
        print(f"PyVista debug → theme: {type(plotter.theme).__name__}, "
              f"interactive={plotter.theme.interactive}, "
              f"off_screen={plotter.off_screen}, "
              f"notebook={plotter.notebook}, "
              f"iren_initialized={iren_initialized}, "
              f"iren_enabled={iren_enabled}")
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
        
        # Create status text actor once
        status_actor = plotter.add_text(
            f"Frame 0/{len(self.frames)-1} | Paused",
            position='upper_left',
            font_size=12,
            name='status'
        )
        
        def set_status():
            status_text = f"Frame {anim_state['frame']}/{len(self.frames)-1} | {'Playing' if anim_state['playing'] else 'Paused'}"
            status_actor.SetText(2, status_text)

        def update_frame(frame_idx, force_render=True):
            """Update mesh to specific frame"""
            positions = self.frames[frame_idx]
            np_positions = np.asarray(positions)
            current_points = mesh.points
            if current_points.shape == np_positions.shape:
                current_points[:] = np_positions
            else:
                mesh.points = np_positions
            mesh.compute_normals(inplace=True)
            # Call modified() if available (VTK method)
            if hasattr(mesh, 'modified'):
                mesh.modified()
            set_status()
            # Only render if window is already shown
            if force_render and hasattr(plotter, '_rendering_initialized'):
                plotter.render()
        
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
        # Use a lambda that accepts optional arguments for wider compatibility
        plotter.add_timer_event(
            max_steps=1_000_000,
            duration=max(int(frame_delay * 1000), 1),
            callback=lambda *args: animation_callback(),
        )
        
        # Key event callbacks - define functions with closures
        def on_space():
            """Toggle play/pause"""
            anim_state['playing'] = not anim_state['playing']
            anim_state['last_update'] = time.time()
            status_text = 'Playing' if anim_state['playing'] else 'Paused'
            print(status_text)
            set_status()
            plotter.render()
        
        def on_right():
            """Step forward"""
            anim_state['playing'] = False
            anim_state['frame'] = min(anim_state['frame'] + 1, len(self.frames) - 1)
            update_frame(anim_state['frame'])
            print(f"Frame {anim_state['frame']}/{len(self.frames)-1}")
        
        def on_left():
            """Step backward"""
            anim_state['playing'] = False
            anim_state['frame'] = max(anim_state['frame'] - 1, 0)
            update_frame(anim_state['frame'])
            print(f"Frame {anim_state['frame']}/{len(self.frames)-1}")

        # Register key events
        print("\nKeyboard controls:")
        print("  space - Toggle play/pause")
        print("  Right - Step forward")
        print("  Left - Step backward")
        print("  q - Quit\n")
        
        plotter.add_key_event('space', on_space)
        plotter.add_key_event('Return', on_space)
        plotter.add_key_event('Right', on_right)
        plotter.add_key_event('d', on_right)
        plotter.add_key_event('Left', on_left)
        plotter.add_key_event('a', on_left)
        plotter.add_key_event('q', lambda: plotter.close())
        plotter.add_key_event('Escape', lambda: plotter.close())
        
        # Set initial frame (without rendering yet)
        update_frame(0, force_render=False)
        anim_state['last_update'] = time.time()
        
        # Mark that we're about to show the window
        plotter._rendering_initialized = True
        
        # Show (this starts the render loop and blocks until window closes)
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
