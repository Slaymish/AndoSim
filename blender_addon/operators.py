import bpy
from bpy.types import Operator
import numpy as np

# Global simulation state for real-time preview
_sim_state = {
    'mesh': None,
    'state': None,
    'constraints': None,
    'params': None,
    'initialized': False,
    'frame': 0,
    'playing': False,
    'debug_contacts': [],  # List of (position, normal) tuples
    'debug_pins': [],  # List of pinned vertex positions
    'stats': {
        'num_contacts': 0,
        'num_pins': 0,
        'last_step_time': 0.0,
    },
}

class ANDO_OT_bake_simulation(Operator):
    """Bake Ando Barrier simulation to cache"""
    bl_idname = "ando.bake_simulation"
    bl_label = "Bake Simulation"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        props = context.scene.ando_barrier
        
        try:
            import ando_barrier_core as abc
        except ImportError:
            self.report({'ERROR'}, "ando_barrier_core module not available. Build the C++ extension first.")
            return {'CANCELLED'}
        
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "No mesh object selected")
            return {'CANCELLED'}
        
        self.report({'INFO'}, f"Baking simulation: {obj.name}")
        
        # Get mesh data
        mesh_data = obj.data
        vertices = np.array([v.co for v in mesh_data.vertices], dtype=np.float32)
        triangles = np.array([p.vertices for p in mesh_data.polygons if len(p.vertices) == 3], dtype=np.int32)
        
        if len(triangles) == 0:
            self.report({'ERROR'}, "Mesh has no triangles. Triangulate the mesh first.")
            return {'CANCELLED'}
        
        self.report({'INFO'}, f"Mesh: {len(vertices)} vertices, {len(triangles)} triangles")
        
        # Initialize material properties
        mat_props = props.material_properties
        material = abc.Material()
        material.youngs_modulus = mat_props.youngs_modulus
        material.poisson_ratio = mat_props.poisson_ratio
        material.density = mat_props.density
        material.thickness = mat_props.thickness
        
        # Initialize simulation parameters
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
        params.enable_strain_limiting = props.enable_strain_limiting
        params.strain_limit = props.strain_limit
        params.strain_tau = props.strain_tau
        
        # Initialize mesh and state
        mesh = abc.Mesh()
        mesh.initialize(vertices, triangles, material)
        
        state = abc.State()
        state.initialize(mesh)
        
        # TODO: Set up constraints from Blender data
        constraints = abc.Constraints()
        
        # Extract pin constraints from vertex group
        pin_group_name = "ando_pins"
        num_pins_added = 0
        if pin_group_name in obj.vertex_groups:
            pin_group = obj.vertex_groups[pin_group_name]
            for i, v in enumerate(mesh_data.vertices):
                try:
                    weight = pin_group.weight(i)
                    if weight > 0.5:  # Threshold for pinning
                        pin_pos = np.array(v.co, dtype=np.float32)
                        constraints.add_pin(i, pin_pos)
                        num_pins_added += 1
                except RuntimeError:
                    pass  # Vertex not in group
            
            self.report({'INFO'}, f"Added {num_pins_added} pin constraints")
        
        # Add ground plane if enabled
        if props.enable_ground_plane:
            ground_normal = np.array([0.0, 0.0, 1.0], dtype=np.float32)  # Blender Z-up
            constraints.add_wall(ground_normal, props.ground_plane_height, params.wall_gap)
            self.report({'INFO'}, "Added ground plane constraint")
        
        # Baking loop
        start_frame = props.cache_start
        end_frame = props.cache_end
        steps_per_frame = max(1, int(1.0 / (props.dt / 1000.0) / 24.0))  # Aim for 24 fps
        
        # Create shape keys for animation
        if not obj.data.shape_keys:
            obj.shape_key_add(name='Basis', from_mix=False)
        basis = obj.data.shape_keys.key_blocks['Basis']
        
        self.report({'INFO'}, f"Baking frames {start_frame} to {end_frame} ({steps_per_frame} steps/frame)")
        
        # Gravity vector (Blender Z-up)
        gravity = np.array([0.0, 0.0, -9.81], dtype=np.float32)
        
        for frame in range(start_frame, end_frame + 1):
            # Create shape key for this frame
            shape_key = obj.shape_key_add(name=f'frame_{frame:04d}', from_mix=False)
            
            # Simulate steps for this frame
            for step in range(steps_per_frame):
                # Apply gravity acceleration
                state.apply_gravity(gravity, params.dt)
                
                # Take physics step
                abc.Integrator.step(mesh, state, constraints, params)
            
            # Update shape key with new positions
            positions = state.get_positions()
            for i in range(len(positions)):
                shape_key.data[i].co = positions[i]
            
            # Set keyframe
            shape_key.value = 0.0
            shape_key.keyframe_insert(data_path='value', frame=frame-1)
            shape_key.value = 1.0
            shape_key.keyframe_insert(data_path='value', frame=frame)
            shape_key.value = 0.0
            shape_key.keyframe_insert(data_path='value', frame=frame+1)
            
            # Progress report
            if frame % 10 == 0:
                self.report({'INFO'}, f"Baked frame {frame}/{end_frame}")
        
        self.report({'INFO'}, f"Baking complete! {end_frame - start_frame + 1} frames")
        
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
        props = context.scene.ando_barrier
        
        try:
            import ando_barrier_core as abc
        except ImportError:
            self.report({'ERROR'}, "ando_barrier_core module not available")
            return {'CANCELLED'}
        
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "No mesh object selected")
            return {'CANCELLED'}
        
        # Get mesh data
        mesh_data = obj.data
        vertices = np.array([v.co for v in mesh_data.vertices], dtype=np.float32)
        triangles = np.array([p.vertices for p in mesh_data.polygons if len(p.vertices) == 3], dtype=np.int32)
        
        if len(triangles) == 0:
            self.report({'ERROR'}, "Mesh has no triangles")
            return {'CANCELLED'}
        
        # Initialize material
        mat_props = props.material_properties
        material = abc.Material()
        material.youngs_modulus = mat_props.youngs_modulus
        material.poisson_ratio = mat_props.poisson_ratio
        material.density = mat_props.density
        material.thickness = mat_props.thickness
        
        # Initialize parameters
        params = abc.SimParams()
        params.dt = props.dt / 1000.0
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
        params.enable_strain_limiting = props.enable_strain_limiting
        params.strain_limit = props.strain_limit
        params.strain_tau = props.strain_tau
        
        # Initialize simulation objects
        mesh = abc.Mesh()
        mesh.initialize(vertices, triangles, material)
        
        state = abc.State()
        state.initialize(mesh)
        
        constraints = abc.Constraints()
        
        # Extract pin constraints
        pin_group_name = "ando_pins"
        num_pins_added = 0
        pin_positions = []
        if pin_group_name in obj.vertex_groups:
            pin_group = obj.vertex_groups[pin_group_name]
            for i, v in enumerate(mesh_data.vertices):
                try:
                    weight = pin_group.weight(i)
                    if weight > 0.5:
                        pin_pos = np.array(v.co, dtype=np.float32)
                        constraints.add_pin(i, pin_pos)
                        pin_positions.append(tuple(pin_pos))
                        num_pins_added += 1
                except RuntimeError:
                    pass
        
        # Add ground plane
        if props.enable_ground_plane:
            ground_normal = np.array([0.0, 0.0, 1.0], dtype=np.float32)
            constraints.add_wall(ground_normal, props.ground_plane_height, params.wall_gap)
        
        # Store in global state
        _sim_state['mesh'] = mesh
        _sim_state['state'] = state
        _sim_state['constraints'] = constraints
        _sim_state['params'] = params
        _sim_state['initialized'] = True
        _sim_state['frame'] = 0
        _sim_state['playing'] = False
        _sim_state['debug_pins'] = pin_positions
        _sim_state['stats']['num_pins'] = num_pins_added
        
        self.report({'INFO'}, f"Initialized: {len(vertices)} vertices, {num_pins_added} pins")
        return {'FINISHED'}

class ANDO_OT_step_simulation(Operator):
    """Step simulation forward one frame"""
    bl_idname = "ando.step_simulation"
    bl_label = "Step Simulation"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        global _sim_state
        
        if not _sim_state['initialized']:
            self.report({'WARNING'}, "Initialize simulation first")
            return {'CANCELLED'}
        
        try:
            import ando_barrier_core as abc
            import time
        except ImportError:
            self.report({'ERROR'}, "ando_barrier_core module not available")
            return {'CANCELLED'}
        
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "No mesh object selected")
            return {'CANCELLED'}
        
        # Retrieve simulation state
        mesh = _sim_state['mesh']
        state = _sim_state['state']
        constraints = _sim_state['constraints']
        params = _sim_state['params']
        
        # Calculate steps per frame (aiming for 24 fps)
        props = context.scene.ando_barrier
        steps_per_frame = max(1, int(1.0 / (props.dt / 1000.0) / 24.0))
        
        # Gravity vector (Blender Z-up)
        gravity = np.array([0.0, 0.0, -9.81], dtype=np.float32)
        
        # Simulate steps for this frame (with timing)
        start_time = time.time()
        for step in range(steps_per_frame):
            state.apply_gravity(gravity, params.dt)
            abc.Integrator.step(mesh, state, constraints, params)
        end_time = time.time()
        
        # Update mesh vertices directly (no shape keys)
        positions = state.get_positions()
        for i, v in enumerate(obj.data.vertices):
            v.co = positions[i]
        
        # Mark mesh as updated
        obj.data.update()
        
        _sim_state['frame'] += 1
        
        # Update statistics
        step_time_ms = (end_time - start_time) * 1000.0 / steps_per_frame
        _sim_state['stats']['last_step_time'] = step_time_ms
        _sim_state['stats']['num_contacts'] = 0  # TODO: Get from C++ when exposed
        _sim_state['stats']['num_pins'] = len(_sim_state['debug_pins'])
        
        # Update debug visualization data
        from . import visualization
        if visualization.is_visualization_enabled():
            # TODO: Get actual contact data from C++
            # For now, just update pins
            visualization.update_debug_data(
                pins=_sim_state['debug_pins'],
                stats=_sim_state['stats']
            )
        
        self.report({'INFO'}, f"Frame {_sim_state['frame']}")
        return {'FINISHED'}

class ANDO_OT_reset_realtime_simulation(Operator):
    """Reset real-time simulation to initial state"""
    bl_idname = "ando.reset_realtime_simulation"
    bl_label = "Reset Real-Time"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        global _sim_state
        
        # Clear simulation state
        _sim_state['mesh'] = None
        _sim_state['state'] = None
        _sim_state['constraints'] = None
        _sim_state['params'] = None
        _sim_state['initialized'] = False
        _sim_state['frame'] = 0
        _sim_state['playing'] = False
        
        # Reset mesh to original positions
        obj = context.active_object
        if obj and obj.type == 'MESH':
            # If there's a shape key basis, restore from it
            if obj.data.shape_keys and 'Basis' in obj.data.shape_keys.key_blocks:
                basis = obj.data.shape_keys.key_blocks['Basis']
                for i, v in enumerate(obj.data.vertices):
                    v.co = basis.data[i].co
                obj.data.update()
        
        self.report({'INFO'}, "Real-time simulation reset")
        return {'FINISHED'}

class ANDO_OT_toggle_play_simulation(Operator):
    """Toggle play/pause for real-time simulation"""
    bl_idname = "ando.toggle_play_simulation"
    bl_label = "Play/Pause"
    bl_options = {'REGISTER', 'UNDO'}
    
    _timer = None
    
    def modal(self, context, event):
        global _sim_state
        
        if event.type == 'ESC' or not _sim_state['playing']:
            return self.cancel(context)
        
        if event.type == 'TIMER':
            # Step simulation
            bpy.ops.ando.step_simulation()
        
        return {'PASS_THROUGH'}
    
    def execute(self, context):
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
        from . import visualization
        
        if visualization.is_visualization_enabled():
            visualization.disable_debug_visualization()
            self.report({'INFO'}, "Debug visualization disabled")
        else:
            visualization.enable_debug_visualization()
            self.report({'INFO'}, "Debug visualization enabled")
        
        return {'FINISHED'}

classes = (
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
