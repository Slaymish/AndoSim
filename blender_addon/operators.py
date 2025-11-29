import bpy
from bpy.types import Operator
import numpy as np
from collections import Counter
from pathlib import Path
from mathutils import Matrix, Vector

from ._core_loader import get_core_module, load_core_from_path


def _core_supports_full_simulation(module) -> bool:
    """Return ``True`` when the imported core exposes the native feature set."""

    required = [
        "Integrator",
        "EnergyTracker",
        "CollisionValidator",
        "AdaptiveTimestep",
        "RigidBody",
    ]
    return all(hasattr(module, name) for name in required)


def _ensure_native_core(reporter, module, context: str) -> bool:
    """Report an actionable error when only the Python fallback is available."""

    if _core_supports_full_simulation(module):
        return True

    message = (
        "The compiled ando_barrier_core extension is required for this operation. "
        "Build it with Blender's bundled Python (see docs/GETTING_STARTED.md) and reinstall the add-on."
    )
    try:
        reporter({'ERROR'}, message)
    except Exception:
        pass
    return False


_BACKEND_ANDO = "ANDO"
_BACKEND_PPF = "PPF"


def _active_backend(context) -> str:
    """Read the currently selected solver backend from add-on preferences."""

    try:
        addon = context.preferences.addons.get(__package__)
    except AttributeError:
        return _BACKEND_ANDO
    if not addon:
        return _BACKEND_ANDO
    return getattr(addon.preferences, "solver_backend", _BACKEND_ANDO)


class ANDO_OT_select_core_module(Operator):
    """Allow users to load a compiled ando_barrier_core module manually."""

    bl_idname = "ando.select_core_module"
    bl_label = "Select Ando Barrier Core Module"
    bl_description = "Load a compiled ando_barrier_core binary to replace the Python fallback"
    bl_options = {'REGISTER'}

    filter_glob: bpy.props.StringProperty(
        default="ando_barrier_core*.so;ando_barrier_core*.pyd;ando_barrier_core*.dll;ando_barrier_core*.dylib",
        options={'HIDDEN'},
    )
    filepath: bpy.props.StringProperty(subtype='FILE_PATH')

    def execute(self, context):
        path = Path(self.filepath)
        if not path.exists():
            self.report({'ERROR'}, f"File not found: {path}")
            return {'CANCELLED'}

        module, error = load_core_from_path(path)
        if module is None:
            detail = error or "Unknown error"
            self.report({'ERROR'}, f"Failed to load module: {detail}")
            return {'CANCELLED'}

        version_attr = getattr(module, "version", None)
        version_label = None
        if callable(version_attr):
            try:
                version_label = version_attr()
            except Exception:  # pragma: no cover - version helper failed
                version_label = None

        if not version_label:
            version_label = path.name

        self.report({'INFO'}, f"Loaded {version_label}")
        return {'FINISHED'}

    def invoke(self, context, event):  # pragma: no cover - Blender UI invocation
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


def _default_stats():
    return {
        'num_contacts': 0,
        'num_pins': 0,
        'last_step_time': 0.0,
        'peak_contacts': 0,
        'contact_counts': {},
        'peak_contact_counts': {},
        # Energy tracking
        'kinetic_energy': 0.0,
        'elastic_energy': 0.0,
        'total_energy': 0.0,
        'initial_energy': 0.0,
        'energy_drift_percent': 0.0,
        'energy_drift_absolute': 0.0,
        'max_velocity': 0.0,
        'linear_momentum': [0.0, 0.0, 0.0],
        'angular_momentum': [0.0, 0.0, 0.0],
        'energy_history': [],  # List of total energy per frame
        'frame_history': [],    # Corresponding frame numbers
        # Collision validation
        'collision_quality': 0,  # 0=excellent, 1=good, 2=warning, 3=error
        'collision_quality_desc': 'Unknown',
        'num_penetrations': 0,
        'max_penetration': 0.0,
        'avg_gap': 0.0,
        'min_gap': 0.0,
        'max_gap': 0.0,
        'ccd_effectiveness': 0.0,
        'max_relative_velocity': 0.0,
        'has_tunneling': False,
        'has_major_penetration': False,
        'num_rigid_bodies': 0,
    }


def _init_material_from_props(abc, props):
    """Initialize a Material object from Blender scene properties.
    
    Args:
        abc: The ando_barrier_core module
        props: Blender scene properties (context.scene.ando_barrier)
    
    Returns:
        Initialized Material object
    """
    mat_props = props.material_properties
    material = abc.Material()
    material.youngs_modulus = mat_props.youngs_modulus
    material.poisson_ratio = mat_props.poisson_ratio
    material.density = mat_props.density
    material.thickness = mat_props.thickness
    return material


def _init_params_from_props(abc, props):
    """Initialize a SimParams object from Blender scene properties.
    
    Args:
        abc: The ando_barrier_core module
        props: Blender scene properties (context.scene.ando_barrier)
    
    Returns:
        Initialized SimParams object
    """
    params = abc.SimParams()
    params.dt = props.dt / 1000.0  # Convert ms to seconds
    params.beta_max = props.beta_max
    params.min_newton_steps = props.min_newton_steps
    params.max_newton_steps = props.max_newton_steps
    params.pcg_tol = props.pcg_tol
    params.pcg_max_iters = props.pcg_max_iters
    params.contact_gap_max = props.contact_gap_max
    params.wall_gap = props.wall_gap
    params.enable_ccd = props.enable_ccd
    params.enable_friction = props.enable_friction
    params.friction_mu = props.friction_mu
    params.friction_epsilon = props.friction_epsilon
    params.velocity_damping = props.velocity_damping
    params.contact_restitution = props.contact_restitution
    params.enable_strain_limiting = props.enable_strain_limiting
    params.strain_limit = props.strain_limit
    params.strain_tau = props.strain_tau
    return params


def _collect_rigid_bodies(context, exclude_obj=None, reporter=None):
    """Convert Blender meshes tagged as rigid colliders into Ando rigid bodies."""

    abc = get_core_module(context="Rigid body extraction")
    if abc is None:
        if reporter:
            reporter({'WARNING'}, "ando_barrier_core module not available; rigid bodies disabled")
        return []
    if not _core_supports_full_simulation(abc):
        if reporter:
            reporter({'WARNING'}, "Compiled ando_barrier_core module missing; rigid colliders disabled")
        return []

    depsgraph = context.evaluated_depsgraph_get()
    rigid_entries = []

    for obj in context.scene.objects:
        if obj.type != 'MESH' or obj is exclude_obj:
            continue

        obj_props = getattr(obj, "ando_barrier_body", None)
        if not obj_props or not obj_props.enabled or obj_props.role != 'RIGID':
            continue

        obj_eval = obj.evaluated_get(depsgraph)
        mesh_eval = obj_eval.to_mesh()

        if mesh_eval is None:
            if reporter:
                reporter({'WARNING'}, f"Rigid collider '{obj.name}' has no mesh data; skipped")
            continue

        mesh_eval.calc_loop_triangles()
        if not mesh_eval.loop_triangles:
            if reporter:
                reporter({'WARNING'}, f"Rigid collider '{obj.name}' has no triangles; skipped")
            obj_eval.to_mesh_clear()
            continue

        world_matrix = obj_eval.matrix_world
        rest_vertices = np.array([world_matrix @ v.co for v in mesh_eval.vertices], dtype=np.float64)
        vertices = rest_vertices.astype(np.float32)
        triangles = np.array(
            [tuple(loop.vertex_index for loop in tri.loops) for tri in mesh_eval.loop_triangles],
            dtype=np.int32,
        )
        obj_eval.to_mesh_clear()

        if len(triangles) == 0:
            if reporter:
                reporter({'WARNING'}, f"Rigid collider '{obj.name}' has zero triangle faces; skipped")
            continue

        body = abc.RigidBody()
        body.initialize(vertices, triangles, obj_props.rigid_density)

        rigid_entries.append({
            'object': obj,
            'body': body,
            'rest_vertices': rest_vertices,
            'initial_matrix': obj.matrix_world.copy(),
            'name': obj.name,
        })

    return rigid_entries


def _compute_rigid_transform(rest_vertices, new_vertices):
    """Find best-fit rigid transform that maps rest vertices to new vertices."""

    if len(rest_vertices) < 3 or len(new_vertices) < 3:
        return None, None

    rest = np.asarray(rest_vertices, dtype=np.float64)
    new = np.asarray(new_vertices, dtype=np.float64)

    rest_center = rest.mean(axis=0)
    new_center = new.mean(axis=0)

    rest_zero = rest - rest_center
    new_zero = new - new_center

    H = rest_zero.T @ new_zero
    try:
        U, _S, Vt = np.linalg.svd(H)
    except np.linalg.LinAlgError:
        return None, None

    R = Vt.T @ U.T
    if np.linalg.det(R) < 0:
        Vt[-1, :] *= -1
        R = Vt.T @ U.T

    t = new_center - R @ rest_center
    return R, t


def _update_rigid_objects(rigid_entries):
    """Update Blender object transforms to follow simulated rigid bodies."""

    if not rigid_entries:
        return

    for entry in rigid_entries:
        body = entry['body']
        obj = entry['object']

        try:
            new_vertices = np.array(body.world_vertices(), dtype=np.float64)
        except AttributeError:
            continue

        if new_vertices.size == 0:
            continue

        transform = _compute_rigid_transform(entry['rest_vertices'], new_vertices)
        if not transform or transform[0] is None:
            continue

        R, t = transform
        rot_mat = Matrix(((R[0, 0], R[0, 1], R[0, 2]),
                          (R[1, 0], R[1, 1], R[1, 2]),
                          (R[2, 0], R[2, 1], R[2, 2])))
        rot_mat.resize_4x4()
        rot_mat.translation = Vector((t[0], t[1], t[2]))
        obj.matrix_world = rot_mat


# Global simulation state for real-time preview
_sim_state = {
    'mesh': None,
    'state': None,
    'constraints': None,
    'params': None,
    'initialized': False,
    'frame': 0,
    'playing': False,
    'debug_contacts': [],  # List of per-contact dicts
    'debug_pins': [],  # List of pinned vertex positions
    'stats': _default_stats(),
    'rigid_entries': [],
    'rigids': [],
    'rigid_objects': [],
}

_ppf_state = {
    'running': False,
    'last_frame': -1,
    'session_dir': None,
    'status': "",
    'operator': None,
}

class ANDO_OT_bake_simulation(Operator):
    """Bake Ando Barrier simulation to cache"""
    bl_idname = "ando.bake_simulation"
    bl_label = "Bake Simulation"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        backend = _active_backend(context)
        if backend != _BACKEND_ANDO:
            self.report({'ERROR'}, "Baking is only available with the Ando backend.")
            return {'CANCELLED'}

        props = context.scene.ando_barrier
        
        abc = get_core_module(context="Bake Simulation operator")
        if abc is None:
            self.report({'ERROR'}, "ando_barrier_core module not available. Build the C++ extension first.")
            return {'CANCELLED'}
        if not _ensure_native_core(self.report, abc, "Bake simulation"):
            return {'CANCELLED'}
        
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "No mesh object selected")
            return {'CANCELLED'}

        obj_role = getattr(obj, "ando_barrier_body", None)
        if obj_role and (not obj_role.enabled or obj_role.role != 'DEFORMABLE'):
            self.report({'WARNING'}, "Active mesh is not tagged as a deformable body in Simulation Setup panel.")

        self.report({'INFO'}, f"Baking simulation: {obj.name}")
        
        # Get mesh data
        mesh_data = obj.data
        matrix_world = obj.matrix_world.copy()
        matrix_world_inv = matrix_world.inverted_safe()
        # Ensure we have triangulated connectivity without modifying the source mesh.
        mesh_data.calc_loop_triangles()
        loop_tris = getattr(mesh_data, "loop_triangles", ())

        if not loop_tris:
            self.report({'ERROR'}, "Mesh has no triangles. Add faces or apply modifiers before baking.")
            return {'CANCELLED'}

        triangles = np.array([tri.vertices for tri in loop_tris], dtype=np.int32)
        vertices = np.array(
            [tuple(matrix_world @ v.co) for v in mesh_data.vertices],
            dtype=np.float32,
        )

        polygon_sides = Counter(len(poly.vertices) for poly in mesh_data.polygons)
        non_tri_faces = sum(count for sides, count in polygon_sides.items() if sides != 3)
        if non_tri_faces:
            self.report(
                {'INFO'},
                f"Auto-triangulated {non_tri_faces} non-tri faces into {len(triangles)} triangles for baking.",
            )
        
        self.report({'INFO'}, f"Mesh: {len(vertices)} vertices, {len(triangles)} triangles")
        
        # Initialize material and simulation parameters using shared helpers
        material = _init_material_from_props(abc, props)
        params = _init_params_from_props(abc, props)
        
        # Initialize mesh and state
        mesh = abc.Mesh()
        mesh.initialize(vertices, triangles, material)
        
        state = abc.State()
        state.initialize(mesh)
        
        # Set up constraints from Blender data
        constraints = abc.Constraints()
        
        # Extract pin constraints from vertex group
        pin_group_name = "ando_pins"
        num_pins_added = 0
        pin_positions_world = []  # Store for later reference
        if pin_group_name in obj.vertex_groups:
            pin_group = obj.vertex_groups[pin_group_name]
            for i, v in enumerate(mesh_data.vertices):
                try:
                    weight = pin_group.weight(i)
                    if weight > 0.5:  # Threshold for pinning
                        # Use world-space coordinates for physics
                        pin_pos_world = matrix_world @ v.co
                        constraints.add_pin(i, np.array(pin_pos_world, dtype=np.float32))
                        # Keep world-space copies for optional debug/visualization
                        pin_positions_world.append(tuple(pin_pos_world))
                        num_pins_added += 1
                except RuntimeError:
                    pass  # Vertex not in group
            
            self.report({'INFO'}, f"Added {num_pins_added} pin constraints")
        else:
            self.report({'WARNING'}, "No 'ando_pins' vertex group found. Use 'Add Pin Constraint' button to create pins.")
        
        # Collect hybrid rigid bodies for collision coupling
        rigid_entries = _collect_rigid_bodies(context, exclude_obj=obj, reporter=self.report)
        rigid_bodies = [entry['body'] for entry in rigid_entries]
        if rigid_entries:
            rigid_names = ", ".join(entry['name'] for entry in rigid_entries[:3])
            if len(rigid_entries) > 3:
                rigid_names += ", …"
            self.report({'INFO'}, f"Using rigid colliders: {rigid_names}")

        # Add ground plane if enabled
        if props.enable_ground_plane:
            ground_normal = np.array([0.0, 0.0, 1.0], dtype=np.float32)  # Blender Z-up
            constraints.add_wall(ground_normal, props.ground_plane_height, params.wall_gap)
            self.report({'INFO'}, f"Added ground plane at Z={props.ground_plane_height}")
        
        # Baking loop
        start_frame = props.cache_start
        end_frame = props.cache_end
        steps_per_frame = max(1, int(1.0 / (props.dt / 1000.0) / 24.0))  # Aim for 24 fps
        
        # Create shape keys for animation
        if not obj.data.shape_keys:
            obj.shape_key_add(name='Basis', from_mix=False)
        else:
            # Clear existing simulation shape keys (keep Basis)
            keys_to_remove = [k for k in obj.data.shape_keys.key_blocks if k.name.startswith('frame_')]
            for key in keys_to_remove:
                obj.shape_key_remove(key)
            self.report({'INFO'}, f"Cleared {len(keys_to_remove)} existing frame keys")
        
        basis = obj.data.shape_keys.key_blocks['Basis']
        
        self.report({'INFO'}, f"Baking frames {start_frame} to {end_frame} ({steps_per_frame} substeps/frame at {props.dt}ms)")
        
        # Gravity vector (Blender Z-up)
        gravity = np.array([0.0, 0.0, -9.81], dtype=np.float32)
        
        # Progress tracking
        total_frames = end_frame - start_frame + 1
        
        # Initialize progress bar
        wm = context.window_manager
        wm.progress_begin(0, total_frames)
        
        try:
            for frame_idx, frame in enumerate(range(start_frame, end_frame + 1)):
                # Update progress bar
                wm.progress_update(frame_idx)
                
                # Check for cancellation (ESC key)
                if context.window_manager.is_interface_locked:
                    self.report({'WARNING'}, "Baking cancelled by user")
                    return {'CANCELLED'}
                
                # Create shape key for this frame
                shape_key = obj.shape_key_add(name=f'frame_{frame:04d}', from_mix=False)
                
                # Simulate steps for this frame
                for step in range(steps_per_frame):
                    # Apply gravity acceleration
                    state.apply_gravity(gravity, params.dt)
                    
                    # Take physics step
                    if rigid_bodies:
                        abc.Integrator.step(mesh, state, constraints, params, rigid_bodies)
                    else:
                        abc.Integrator.step(mesh, state, constraints, params)
                
                # Update shape key with new positions
                positions_world = state.get_positions()
                for i in range(len(positions_world)):
                    world_vec = Vector(positions_world[i].tolist())
                    local_vec = matrix_world_inv @ world_vec
                    shape_key.data[i].co = local_vec
                
                # Set keyframe for shape key animation
                shape_key.value = 0.0
                shape_key.keyframe_insert(data_path='value', frame=frame-1)
                shape_key.value = 1.0
                shape_key.keyframe_insert(data_path='value', frame=frame)
                shape_key.value = 0.0
                shape_key.keyframe_insert(data_path='value', frame=frame+1)
                
                # Progress report every 10 frames or at 25%, 50%, 75%, 100%
                progress_pct = (frame_idx + 1) * 100 // total_frames
                if frame % 10 == 0 or progress_pct in [25, 50, 75, 100]:
                    self.report({'INFO'}, f"Baking progress: {frame}/{end_frame} ({progress_pct}%)")
        finally:
            # Always clean up progress bar
            wm.progress_end()
        
        # Final report with statistics
        num_pins = constraints.num_active_pins()
        self.report({'INFO'}, f"✓ Baking complete! {total_frames} frames with {num_pins} pins and {num_pins_added} pinned vertices")
        
        return {'FINISHED'}

class ANDO_OT_reset_simulation(Operator):
    """Reset simulation to initial state"""
    bl_idname = "ando.reset_simulation"
    bl_label = "Reset Simulation"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "No mesh object selected")
            return {'CANCELLED'}
        
        # Remove all shape keys except Basis
        if obj.data.shape_keys:
            # Remove all keys except basis
            keys_to_remove = [key for key in obj.data.shape_keys.key_blocks if key.name != 'Basis']
            for key in keys_to_remove:
                obj.shape_key_remove(key)
            
            self.report({'INFO'}, f"Removed {len(keys_to_remove)} shape keys from {obj.name}")
            
            # Remove keyframe animation data if present
            if obj.data.shape_keys.animation_data:
                obj.data.shape_keys.animation_data_clear()
                self.report({'INFO'}, "Cleared shape key animation data")
        else:
            self.report({'INFO'}, "No shape keys to remove")
        
        return {'FINISHED'}

class ANDO_OT_add_pin_constraint(Operator):
    """Add pin constraint to selected vertices"""
    bl_idname = "ando.add_pin_constraint"
    bl_label = "Add Pin Constraint"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        if obj and obj.type == 'MESH':
            # Get or create vertex group
            vg_name = "ando_pins"
            if vg_name not in obj.vertex_groups:
                vg = obj.vertex_groups.new(name=vg_name)
            else:
                vg = obj.vertex_groups[vg_name]
            
            # Add selected vertices to group
            if obj.mode == 'EDIT':
                bpy.ops.object.mode_set(mode='OBJECT')
                selected_verts = [v for v in obj.data.vertices if v.select]
                for v in selected_verts:
                    vg.add([v.index], 1.0, 'ADD')
                bpy.ops.object.mode_set(mode='EDIT')
                self.report({'INFO'}, f"Added {len(selected_verts)} pinned vertices to {obj.name}")
            else:
                self.report({'WARNING'}, "Enter Edit Mode and select vertices first")
                return {'CANCELLED'}
        else:
            self.report({'ERROR'}, "No mesh object selected")
            return {'CANCELLED'}
        return {'FINISHED'}

class ANDO_OT_add_wall_constraint(Operator):
    """Add wall constraint from active face normal"""
    bl_idname = "ando.add_wall_constraint"
    bl_label = "Add Wall from Face"
    bl_options = {'REGISTER', 'UNDO'}
    
    normal: bpy.props.FloatVectorProperty(
        name="Normal",
        default=(0.0, 0.0, 1.0),
        size=3,
    )
    
    offset: bpy.props.FloatProperty(
        name="Offset",
        default=0.0,
    )
    
    def execute(self, context):
        props = context.scene.ando_barrier
        
        # For now, just update ground plane settings
        props.enable_ground_plane = True
        props.ground_plane_height = self.offset
        
        self.report({'INFO'}, f"Ground plane enabled at height {self.offset}")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class ANDO_OT_init_realtime_simulation(Operator):
    """Initialize real-time simulation"""

    bl_idname = "ando.init_realtime_simulation"
    bl_label = "Initialize Real-Time Simulation"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        global _sim_state
        global _ppf_state

        backend = _active_backend(context)
        self._using_ppf = backend == _BACKEND_PPF

        if self._using_ppf:
            try:
                from . import ppf_adapter
            except Exception as exc:  # pragma: no cover - Blender import guard
                message = f"Failed to import PPF adapter: {exc}"
                self.report({'ERROR'}, message)
                _ppf_state['running'] = False
                _ppf_state['operator'] = None
                _ppf_state['status'] = message
                _ppf_state['session_dir'] = None
                return {'CANCELLED'}

            result = ppf_adapter.PPFSession.start_modal(self, context)
            info = getattr(self, "_ppf", None) or {}
            outdir = info.get('outdir')
            _ppf_state['running'] = result == {'RUNNING_MODAL'}
            _ppf_state['last_frame'] = info.get('last_frame', -1)
            _ppf_state['session_dir'] = str(outdir) if outdir else None
            _ppf_state['status'] = "Running" if _ppf_state['running'] else ppf_adapter.ppf_status_message()
            _ppf_state['operator'] = self if _ppf_state['running'] else None
            return result

        # Reset any lingering PPF state when running the native backend
        _ppf_state['running'] = False
        _ppf_state['operator'] = None
        _ppf_state['status'] = ""
        _ppf_state['session_dir'] = None

        props = context.scene.ando_barrier

        abc = get_core_module(context="Real-time simulation initialization")
        if abc is None:
            self.report({'ERROR'}, "ando_barrier_core module not available")
            return {'CANCELLED'}
        if not _ensure_native_core(self.report, abc, "Real-time simulation"):
            return {'CANCELLED'}

        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "No mesh object selected")
            return {'CANCELLED'}

        obj_role = getattr(obj, "ando_barrier_body", None)
        if obj_role and (not obj_role.enabled or obj_role.role != 'DEFORMABLE'):
            self.report({'WARNING'}, "Active mesh is not tagged as a deformable body in Simulation Setup panel.")

        # Get mesh data
        mesh_data = obj.data
        matrix_world = obj.matrix_world.copy()
        matrix_world_inv = matrix_world.inverted_safe()
        vertices = np.array(
            [tuple(matrix_world @ v.co) for v in mesh_data.vertices],
            dtype=np.float32,
        )
        triangles = np.array([p.vertices for p in mesh_data.polygons if len(p.vertices) == 3], dtype=np.int32)

        if len(triangles) == 0:
            self.report({'ERROR'}, "Mesh has no triangles")
            return {'CANCELLED'}

        # Initialize material and simulation parameters using shared helpers
        material = _init_material_from_props(abc, props)
        params = _init_params_from_props(abc, props)

        # Initialize simulation objects
        mesh = abc.Mesh()
        mesh.initialize(vertices, triangles, material)

        state = abc.State()
        state.initialize(mesh)

        constraints = abc.Constraints()

        # Extract pin constraints
        pin_group_name = "ando_pins"
        num_pins_added = 0
        pin_positions_world = []
        if pin_group_name in obj.vertex_groups:
            pin_group = obj.vertex_groups[pin_group_name]
            for i, v in enumerate(mesh_data.vertices):
                try:
                    weight = pin_group.weight(i)
                    if weight > 0.5:
                        pin_pos_world = matrix_world @ v.co
                        constraints.add_pin(i, np.array(pin_pos_world, dtype=np.float32))
                        pin_positions_world.append(tuple(pin_pos_world))
                        num_pins_added += 1
                except RuntimeError:
                    pass

        # Add ground plane
        if props.enable_ground_plane:
            ground_normal = np.array([0.0, 0.0, 1.0], dtype=np.float32)
            constraints.add_wall(ground_normal, props.ground_plane_height, params.wall_gap)

        # Discover rigid colliders participating in hybrid simulation
        rigid_entries = _collect_rigid_bodies(context, exclude_obj=obj, reporter=self.report)
        rigid_bodies = [entry['body'] for entry in rigid_entries]
        if rigid_entries:
            names = ", ".join(entry['name'] for entry in rigid_entries[:3])
            if len(rigid_entries) > 3:
                names += ", …"
            self.report({'INFO'}, f"Linked rigid colliders: {names}")

        # Store in global state
        _sim_state['mesh'] = mesh
        _sim_state['state'] = state
        _sim_state['constraints'] = constraints
        _sim_state['params'] = params
        _sim_state['initialized'] = True
        _sim_state['frame'] = 0
        _sim_state['playing'] = False
        _sim_state['stats'] = _default_stats()
        _sim_state['debug_pins'] = pin_positions_world
        _sim_state['stats']['num_pins'] = num_pins_added
        _sim_state['rigid_entries'] = rigid_entries
        _sim_state['rigids'] = rigid_bodies
        _sim_state['rigid_objects'] = [entry['object'] for entry in rigid_entries]
        _sim_state['stats']['num_rigid_bodies'] = len(rigid_entries)
        _sim_state['matrix_world'] = matrix_world
        _sim_state['matrix_world_inv'] = matrix_world_inv

        self.report({'INFO'}, f"Initialized: {len(vertices)} vertices, {num_pins_added} pins")
        return {'FINISHED'}

    def modal(self, context, event):
        global _ppf_state

        if not getattr(self, "_using_ppf", False):
            return {'FINISHED'}

        try:
            from . import ppf_adapter
        except Exception as exc:  # pragma: no cover - Blender import guard
            self.report({'ERROR'}, f"PPF adapter error: {exc}")
            _ppf_state['running'] = False
            _ppf_state['operator'] = None
            _ppf_state['status'] = str(exc)
            _ppf_state['session_dir'] = None
            return {'CANCELLED'}

        if event.type == 'ESC':
            ppf_adapter.PPFSession.cleanup(self)
            _ppf_state['running'] = False
            _ppf_state['operator'] = None
            _ppf_state['status'] = "Cancelled"
            _ppf_state['session_dir'] = None
            return {'CANCELLED'}

        status = ppf_adapter.PPFSession.modal_tick(self, context, event)
        info = getattr(self, "_ppf", None)
        if info:
            _ppf_state['last_frame'] = info.get('last_frame', -1)
            outdir = info.get('outdir')
            if outdir:
                _ppf_state['session_dir'] = str(outdir)

        if status in ({'FINISHED'}, {'CANCELLED'}):
            _ppf_state['running'] = False
            _ppf_state['operator'] = None
            _ppf_state['status'] = "Finished" if status == {'FINISHED'} else "Cancelled"
            if status == {'CANCELLED'}:
                ppf_adapter.PPFSession.cleanup(self)
            if status == {'FINISHED'} and info and info.get('outdir'):
                _ppf_state['session_dir'] = str(info['outdir'])
            return status

        return status

    def cancel(self, context):
        global _ppf_state

        if getattr(self, "_using_ppf", False):
            try:
                from . import ppf_adapter
            except Exception:
                _ppf_state['running'] = False
                _ppf_state['operator'] = None
                _ppf_state['status'] = "Cancelled"
                _ppf_state['session_dir'] = None
                return {'CANCELLED'}

            ppf_adapter.PPFSession.cleanup(self)
            _ppf_state['running'] = False
            _ppf_state['operator'] = None
            _ppf_state['status'] = "Cancelled"
            _ppf_state['session_dir'] = None
        return {'CANCELLED'}

class ANDO_OT_step_simulation(Operator):
    """Step simulation forward one frame"""
    bl_idname = "ando.step_simulation"
    bl_label = "Step Simulation"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        global _sim_state
        
        backend = _active_backend(context)
        if backend != _BACKEND_ANDO:
            self.report({'WARNING'}, "Real-time stepping is only available with the Ando backend.")
            return {'CANCELLED'}

        if not _sim_state['initialized']:
            self.report({'WARNING'}, "Initialize simulation first")
            return {'CANCELLED'}
        
        abc = get_core_module(context="Simulation step operator")
        if abc is None:
            self.report({'ERROR'}, "ando_barrier_core module not available")
            return {'CANCELLED'}
        if not _ensure_native_core(self.report, abc, "Simulation step"):
            return {'CANCELLED'}
        import time
        
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "No mesh object selected")
            return {'CANCELLED'}
        
        # Retrieve simulation state
        mesh = _sim_state['mesh']
        state = _sim_state['state']
        constraints = _sim_state['constraints']
        params = _sim_state['params']
        rigid_bodies = _sim_state.get('rigids', [])

        # Adaptive timestepping (if enabled)
        props = context.scene.ando_barrier
        if props.enable_adaptive_dt:
            # Compute next timestep using CFL condition
            velocities = state.get_velocities()
            current_dt_sec = params.dt  # In seconds
            dt_min_sec = props.dt_min / 1000.0  # Convert ms to seconds
            dt_max_sec = props.dt_max / 1000.0
            
            new_dt_sec = abc.AdaptiveTimestep.compute_next_dt(
                velocities, mesh, current_dt_sec,
                dt_min_sec, dt_max_sec, props.cfl_safety_factor
            )
            
            # Update params
            params.dt = new_dt_sec
            
            # Store dt history for diagnostics
            if 'dt_history' not in _sim_state['stats']:
                _sim_state['stats']['dt_history'] = []
            _sim_state['stats']['dt_history'].append(new_dt_sec * 1000.0)  # Store as ms
            if len(_sim_state['stats']['dt_history']) > 100:
                _sim_state['stats']['dt_history'].pop(0)
        
        # Calculate steps per frame (aiming for 24 fps)
        steps_per_frame = max(1, int(1.0 / (props.dt / 1000.0) / 24.0))
        
        # Gravity vector (Blender Z-up)
        gravity = np.array([0.0, 0.0, -9.81], dtype=np.float32)
        
        # Simulate steps for this frame (with timing)
        start_time = time.time()
        for step in range(steps_per_frame):
            state.apply_gravity(gravity, params.dt)
            if rigid_bodies:
                abc.Integrator.step(mesh, state, constraints, params, rigid_bodies)
            else:
                abc.Integrator.step(mesh, state, constraints, params)
        end_time = time.time()

        # Compute energy diagnostics
        energy_diag = abc.EnergyTracker.compute(mesh, state, constraints, params)
        
        # Get stats reference
        stats = _sim_state['stats']
        
        # Update energy drift tracking
        if _sim_state['frame'] == 0:
            # First frame: initialize baseline energy
            stats['initial_energy'] = energy_diag.total_energy
        else:
            # Track drift from initial energy
            if stats['initial_energy'] > 1e-12:
                drift_abs = energy_diag.total_energy - stats['initial_energy']
                drift_pct = (drift_abs / stats['initial_energy']) * 100.0
                stats['energy_drift_absolute'] = drift_abs
                stats['energy_drift_percent'] = drift_pct
        
        # Update current energy values
        stats['kinetic_energy'] = energy_diag.kinetic_energy
        stats['elastic_energy'] = energy_diag.elastic_energy
        stats['total_energy'] = energy_diag.total_energy
        stats['max_velocity'] = energy_diag.max_velocity
        stats['linear_momentum'] = energy_diag.linear_momentum
        stats['angular_momentum'] = energy_diag.angular_momentum
        
        # Add to energy history (limit to last 100 frames to avoid memory growth)
        stats['energy_history'].append(energy_diag.total_energy)
        stats['frame_history'].append(_sim_state['frame'])
        if len(stats['energy_history']) > 100:
            stats['energy_history'].pop(0)
            stats['frame_history'].pop(0)
        
        # Update mesh vertices directly (no shape keys)
        matrix_world_inv = _sim_state.get('matrix_world_inv')
        if matrix_world_inv is None:
            matrix_world_inv = obj.matrix_world.inverted_safe()
            _sim_state['matrix_world_inv'] = matrix_world_inv

        positions_world = state.get_positions()
        for i, v in enumerate(obj.data.vertices):
            world_vec = Vector(positions_world[i].tolist())
            v.co = matrix_world_inv @ world_vec

        # Mark mesh as updated
        obj.data.update()

        # Update rigid body transforms in Blender
        _update_rigid_objects(_sim_state.get('rigid_entries', []))
        _sim_state['rigid_objects'] = [entry['object'] for entry in _sim_state.get('rigid_entries', [])]

        _sim_state['frame'] += 1
        
        # Update statistics
        step_time_ms = (end_time - start_time) * 1000.0 / steps_per_frame
        _sim_state['stats']['last_step_time'] = step_time_ms
        _sim_state['stats']['num_pins'] = len(_sim_state['debug_pins'])
        
        # Collect contact data for visualization and statistics
        if rigid_bodies:
            contacts = abc.Integrator.compute_contacts(mesh, state, rigid_bodies)
        else:
            contacts = abc.Integrator.compute_contacts(mesh, state)
        
        # Compute collision validation metrics
        collision_metrics = abc.CollisionValidator.compute_metrics(
            mesh, state, contacts, params.contact_gap_max, params.enable_ccd
        )
        
        debug_contacts = []
        contact_counter = Counter()
        for contact in contacts:
            # Convert Eigen vectors to plain Python tuples for Blender GPU API
            contact_pos = tuple(float(x) for x in np.asarray(contact.witness_p))
            contact_normal = tuple(float(x) for x in np.asarray(contact.normal))
            contact_type = getattr(contact.type, "name", str(contact.type))
            if isinstance(contact_type, str) and contact_type.startswith("ContactType."):
                contact_type = contact_type.split(".", 1)[1]
            debug_contacts.append({
                'position': contact_pos,
                'normal': contact_normal,
                'type': contact_type,
            })
            contact_counter[contact_type] += 1
        
        _sim_state['debug_contacts'] = debug_contacts
        stats = _sim_state['stats']
        current_count = len(debug_contacts)
        stats['num_contacts'] = current_count
        stats['contact_counts'] = dict(contact_counter)
        stats['peak_contacts'] = max(stats.get('peak_contacts', 0), current_count)
        
        # Update collision quality metrics
        stats['collision_quality'] = collision_metrics.quality_level()
        stats['collision_quality_desc'] = collision_metrics.quality_description()
        stats['num_penetrations'] = collision_metrics.num_penetrations
        stats['max_penetration'] = collision_metrics.max_penetration
        stats['avg_gap'] = collision_metrics.avg_gap
        stats['min_gap'] = collision_metrics.min_gap
        stats['max_gap'] = collision_metrics.max_gap
        stats['ccd_effectiveness'] = collision_metrics.ccd_effectiveness
        stats['max_relative_velocity'] = collision_metrics.max_relative_velocity
        stats['has_tunneling'] = collision_metrics.has_tunneling
        stats['has_major_penetration'] = collision_metrics.has_major_penetration
        peak_by_type = dict(stats.get('peak_contact_counts', {}))
        for ctype, count in contact_counter.items():
            peak_by_type[ctype] = max(peak_by_type.get(ctype, 0), count)
        stats['peak_contact_counts'] = peak_by_type
        
        # Update debug visualization data
        from . import visualization
        if visualization.is_visualization_enabled():
            visualization.update_debug_data(
                contacts=debug_contacts,
                pins=_sim_state['debug_pins'],
                stats=_sim_state['stats']
            )
            
            # Update heatmaps if enabled
            props = context.scene.ando_barrier
            if props.show_gap_heatmap:
                # Convert contacts to format needed by heatmap
                heatmap_contacts = []
                for c in contacts:
                    heatmap_contacts.append({
                        'position': tuple(float(x) for x in np.asarray(c.witness_p)),
                        'gap': float(c.gap) if hasattr(c, 'gap') else props.contact_gap_max,
                    })
                visualization.update_gap_heatmap(obj, heatmap_contacts, props.contact_gap_max)
            
            if props.show_strain_overlay:
                visualization.update_strain_heatmap(obj, state, props.strain_limit / 100.0)
        
        self.report({'INFO'}, f"Frame {_sim_state['frame']}")
        return {'FINISHED'}

class ANDO_OT_reset_realtime_simulation(Operator):
    """Reset real-time simulation to initial state"""
    bl_idname = "ando.reset_realtime_simulation"
    bl_label = "Reset Real-Time"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        global _sim_state
        global _ppf_state

        backend = _active_backend(context)
        if backend == _BACKEND_PPF:
            operator = _ppf_state.get('operator')
            if operator:
                try:
                    from . import ppf_adapter
                    ppf_adapter.PPFSession.cleanup(operator)
                except Exception:
                    pass
            _ppf_state['running'] = False
            _ppf_state['operator'] = None
            _ppf_state['status'] = "Reset"
            _ppf_state['session_dir'] = None
            _ppf_state['last_frame'] = -1
            self.report({'INFO'}, "PPF session cleared")
            return {'FINISHED'}
        
        # Clear simulation state
        _sim_state['mesh'] = None
        _sim_state['state'] = None
        _sim_state['constraints'] = None
        _sim_state['params'] = None
        _sim_state['initialized'] = False
        _sim_state['frame'] = 0
        _sim_state['playing'] = False
        _sim_state['debug_contacts'] = []
        _sim_state['debug_pins'] = []
        _sim_state['stats'] = _default_stats()
        rigid_entries = _sim_state.get('rigid_entries', [])
        _sim_state['rigid_entries'] = []
        _sim_state['rigids'] = []
        _sim_state['rigid_objects'] = []

        # Reset mesh to original positions
        obj = context.active_object
        if obj and obj.type == 'MESH':
            # If there's a shape key basis, restore from it
            if obj.data.shape_keys and 'Basis' in obj.data.shape_keys.key_blocks:
                basis = obj.data.shape_keys.key_blocks['Basis']
                for i, v in enumerate(obj.data.vertices):
                    v.co = basis.data[i].co
                obj.data.update()

        # Restore rigid colliders to their starting transforms
        for entry in rigid_entries:
            entry['object'].matrix_world = entry['initial_matrix']

        self.report({'INFO'}, "Real-time simulation reset")
        return {'FINISHED'}

class ANDO_OT_toggle_play_simulation(Operator):
    """Toggle play/pause for real-time simulation"""
    bl_idname = "ando.toggle_play_simulation"
    bl_label = "Play/Pause"
    bl_options = {'REGISTER', 'UNDO'}
    
    _timer = None
    
    def modal(self, context, event):
        if _active_backend(context) != _BACKEND_ANDO:
            return {'CANCELLED'}
        
        global _sim_state
        
        if event.type == 'ESC' or not _sim_state['playing']:
            return self.cancel(context)
        
        if event.type == 'TIMER':
            # Step simulation
            bpy.ops.ando.step_simulation()
        
        return {'PASS_THROUGH'}
    
    def execute(self, context):
        if _active_backend(context) != _BACKEND_ANDO:
            self.report({'WARNING'}, "Interactive playback is only available with the Ando backend.")
            return {'CANCELLED'}

        global _sim_state
        
        if not _sim_state['initialized']:
            self.report({'WARNING'}, "Initialize simulation first")
            return {'CANCELLED'}
        
        # Toggle playing state
        _sim_state['playing'] = not _sim_state['playing']
        
        if _sim_state['playing']:
            # Start playing
            wm = context.window_manager
            self._timer = wm.event_timer_add(1.0 / 24.0, window=context.window)  # 24 fps
            wm.modal_handler_add(self)
            self.report({'INFO'}, "Simulation playing (ESC to stop)")
            return {'RUNNING_MODAL'}
        else:
            # Stop playing
            self.report({'INFO'}, "Simulation paused")
            return {'FINISHED'}
    
    def cancel(self, context):
        global _sim_state
        _sim_state['playing'] = False
        
        if self._timer:
            wm = context.window_manager
            wm.event_timer_remove(self._timer)
            self._timer = None
        
        return {'CANCELLED'}

class ANDO_OT_toggle_debug_visualization(Operator):
    """Toggle debug visualization overlay"""
    bl_idname = "ando.toggle_debug_visualization"
    bl_label = "Toggle Debug Visualization"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        if _active_backend(context) != _BACKEND_ANDO:
            self.report({'INFO'}, "Debug visualization is only available with the Ando backend.")
            return {'CANCELLED'}

        from . import visualization
        
        if visualization.is_visualization_enabled():
            visualization.disable_debug_visualization()
            self.report({'INFO'}, "Debug visualization disabled")
        else:
            visualization.enable_debug_visualization()
            self.report({'INFO'}, "Debug visualization enabled")
        
        return {'FINISHED'}

classes = (
    ANDO_OT_select_core_module,
    ANDO_OT_bake_simulation,
    ANDO_OT_reset_simulation,
    ANDO_OT_add_pin_constraint,
    ANDO_OT_add_wall_constraint,
    ANDO_OT_init_realtime_simulation,
    ANDO_OT_step_simulation,
    ANDO_OT_reset_realtime_simulation,
    ANDO_OT_toggle_play_simulation,
    ANDO_OT_toggle_debug_visualization,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
