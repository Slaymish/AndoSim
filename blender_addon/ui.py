import logging
from pathlib import Path

import bpy
from bpy.types import Panel

from ._core_loader import get_core_module

_LOGGER = logging.getLogger(__name__)
_LOGGED_REALTIME_CORE_FAILURE = False
_LOGGED_OPERATOR_IMPORT_FAILURE = False

_BACKEND_ANDO = "ANDO"
_BACKEND_PPF = "PPF"


def _core_path_hint(core_module=None) -> str:
    """Return the most relevant path to the compiled core module."""

    module_file = getattr(core_module, "__file__", None) if core_module else None
    if module_file:
        module_path = Path(module_file)
        try:
            return str(module_path.resolve())
        except OSError:
            return str(module_path)

    try:
        addon_root = Path(__file__).resolve().parent
    except OSError:
        addon_root = Path(__file__).parent

    patterns = (
        "ando_barrier_core*.so",
        "ando_barrier_core*.pyd",
        "ando_barrier_core*.dll",
        "ando_barrier_core*.dylib",
        "ando_barrier_core.py",
    )

    for pattern in patterns:
        for candidate in sorted(addon_root.glob(pattern)):
            if candidate.exists():
                try:
                    return str(candidate.resolve())
                except OSError:
                    return str(candidate)

    try:
        return str(addon_root.resolve())
    except OSError:
        return str(addon_root)


def _count_sim_objects(context):
    deformable = 0
    rigid = 0
    for obj in context.scene.objects:
        props = getattr(obj, "ando_barrier_body", None)
        if not props or not props.enabled:
            continue
        if props.role == 'DEFORMABLE':
            deformable += 1
        elif props.role == 'RIGID':
            rigid += 1
    return deformable, rigid


def _get_scene_props(context):
    """Safely retrieve the scene-level Ando properties, or None if unavailable."""
    scene = getattr(context, "scene", None)
    if scene is None:
        return None
    props = getattr(scene, "ando_barrier", None)
    if props is None or not hasattr(props, "rna_type"):
        return None
    return props


def _active_backend(context) -> str:
    """Read the active solver backend from add-on preferences."""

    try:
        addon = context.preferences.addons.get(__package__)
    except AttributeError:
        return _BACKEND_ANDO
    if not addon:
        return _BACKEND_ANDO
    return getattr(addon.preferences, "solver_backend", _BACKEND_ANDO)


def _configure_layout(layout):
    """Apply a consistent, compact style to Blender UI panels."""
    layout.use_property_split = True
    layout.use_property_decorate = False
    return layout


def _draw_ppf_session(layout):
    """Render real-time controls for the PPF backend."""
    try:
        from . import operators, ppf_adapter
    except ImportError as exc:  # pragma: no cover - Blender import guard
        status_box = layout.box()
        row = status_box.row()
        row.alert = True
        row.label(text="PPF controls unavailable.", icon='ERROR')
        status_box.label(text=str(exc), icon='INFO')

        controls = layout.row()
        controls.enabled = False
        controls.operator("ando.init_realtime_simulation", text="Start PPF Session", icon='PLAY')
        return

    available, message = ppf_adapter.ppf_status()
    status_box = layout.box()
    status_row = status_box.row(align=True)
    status_row.alert = not available
    status_icon = 'CHECKMARK' if available else 'ERROR'
    status_row.label(text=message, icon=status_icon)

    state = getattr(operators, "_ppf_state", {})
    running = state.get('running', False)
    last_frame = state.get('last_frame', -1)
    session_dir = state.get('session_dir')

    controls = layout.row(align=True)
    controls.enabled = available and not running
    controls.operator(
        "ando.init_realtime_simulation",
        text="Start PPF Session" if not running else "Solver Running",
        icon='PLAY',
    )

    info_box = layout.box()
    if session_dir:
        info_box.label(text=f"Output: {session_dir}", icon='FILE_FOLDER')

    if running:
        info = info_box.column(align=True)
        info.label(text="Streaming results to Blender.", icon='INFO')
        if last_frame is not None and last_frame >= 0:
            info.label(text=f"Last frame received: {last_frame}", icon='TIME')
        info_box.operator("ando.reset_realtime_simulation", text="Terminate Session", icon='CANCEL')
    else:
        idle = info_box.row(align=True)
        idle.alert = not available
        idle_icon = 'PLAY' if available else 'ERROR'
        idle.label(
            text="Ready to launch PPF session" if available else "Resolve issues above to enable PPF",
            icon=idle_icon,
        )
        info_box.operator("ando.reset_realtime_simulation", text="Clear Session Data", icon='FILE_REFRESH')


def _draw_ando_session(layout, context):
    """Render real-time controls for the native Ando backend."""
    core_module = get_core_module(context="Real-time preview panel")
    core_hint = _core_path_hint(core_module)

    global _LOGGED_REALTIME_CORE_FAILURE  # pylint: disable=global-statement
    global _LOGGED_OPERATOR_IMPORT_FAILURE  # pylint: disable=global-statement

    if core_module is None:
        status_box = layout.box()
        row = status_box.row()
        row.alert = True
        row.label(text="Core module unavailable; real-time preview disabled.", icon='ERROR')
        status_box.label(text="Check the console for the resolved search path.", icon='INFO')

        controls = layout.row()
        controls.enabled = False
        controls.operator("ando.init_realtime_simulation", text="Initialize", icon='PLAY')

        if not _LOGGED_REALTIME_CORE_FAILURE:
            _LOGGER.error(
                "Real-time preview initialization blocked: ando_barrier_core not found. Resolved search path: %s",
                core_hint,
            )
            _LOGGED_REALTIME_CORE_FAILURE = True
        return

    try:
        from . import operators
    except ImportError as exc:  # pragma: no cover - Blender import guard
        status_box = layout.box()
        row = status_box.row()
        row.alert = True
        row.label(text="Failed to load real-time controls.", icon='ERROR')
        status_box.label(text="See console for diagnostics.", icon='INFO')

        controls = layout.row()
        controls.enabled = False
        controls.operator("ando.init_realtime_simulation", text="Initialize", icon='PLAY')

        if not _LOGGED_OPERATOR_IMPORT_FAILURE:
            _LOGGER.error(
                "Real-time preview initialization failed to import operators (core hint: %s): %s",
                core_hint,
                exc,
            )
            _LOGGED_OPERATOR_IMPORT_FAILURE = True
        return

    _LOGGED_REALTIME_CORE_FAILURE = False
    _LOGGED_OPERATOR_IMPORT_FAILURE = False

    sim_state = operators._sim_state

    if sim_state['initialized']:
        status_box = layout.box()
        header = status_box.row(align=True)
        header.label(text=f"Frame {sim_state['frame']}", icon='TIME')

        rigid_objs = [obj for obj in sim_state.get('rigid_objects', []) if obj]
        if rigid_objs:
            names = ", ".join(obj.name for obj in rigid_objs[:2])
            if len(rigid_objs) > 2:
                names += ", …"
            status_box.label(text=f"Rigid colliders: {names}", icon='CUBE')
        elif _count_sim_objects(context)[1] > 0:
            status_box.label(text="Rigid colliders configured; reinitialize to sync.", icon='INFO')

        controls = layout.row(align=True)
        play_icon = 'PAUSE' if sim_state['playing'] else 'PLAY'
        play_text = "Pause" if sim_state['playing'] else "Play"
        controls.operator("ando.toggle_play_simulation", text=play_text, icon=play_icon)
        controls.operator("ando.step_simulation", text="Step", icon='FRAME_NEXT')
        controls.operator("ando.reset_realtime_simulation", text="Reset", icon='FILE_REFRESH')

        param_box = layout.box()
        param_box.label(text="Parameter Sync", icon='SETTINGS')
        param_box.operator("ando.update_parameters", text="Apply Scene Changes", icon='FILE_REFRESH')
        param_box.label(text="Push updated materials and settings into the running solver.", icon='INFO')
    else:
        layout.label(text="Simulation not initialized.", icon='INFO')
        layout.operator("ando.init_realtime_simulation", text="Initialize", icon='PLAY')


class ANDO_PT_main_panel(Panel):
    """Main panel for Ando Barrier Physics"""
    bl_label = "Ando Barrier Physics"
    bl_idname = "ANDO_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Ando Physics'
    
    def draw(self, context):
        layout = _configure_layout(self.layout)
        props = _get_scene_props(context)

        backend = _active_backend(context)
        backend_label = "Ando Core" if backend == _BACKEND_ANDO else "PPF Contact Solver"

        status_box = layout.box()
        status_header = status_box.row(align=True)
        status_header.label(text="Solver Backend", icon='MOD_PHYSICS')
        status_header.label(text=backend_label)

        if backend == _BACKEND_ANDO:
            core_module = get_core_module(context="UI status check")
            if core_module is None:
                warning = status_box.row()
                warning.alert = True
                warning.label(text="Core module not loaded — build the C++ extension and reload.", icon='ERROR')
                return

            version_row = status_box.row(align=True)
            try:
                version_row.label(text=f"Core ready • {core_module.version()}", icon='CHECKMARK')
            except AttributeError:
                version_row.label(text="Core module loaded", icon='CHECKMARK')
        else:
            try:
                from . import ppf_adapter
            except Exception as exc:  # pragma: no cover - Blender import guard
                warning = status_box.row()
                warning.alert = True
                warning.label(text=f"PPF adapter import failed: {exc}", icon='ERROR')
            else:
                available, message = ppf_adapter.ppf_status()
                status = status_box.row()
                status.alert = not available
                icon = 'CHECKMARK' if available else 'ERROR'
                status.label(text=message, icon=icon)

        if props is None:
            layout.label(text="Scene properties unavailable", icon='ERROR')
            layout.label(text="Re-enable the add-on or reopen the file.", icon='INFO')
            return

        timing_box = layout.box()
        timing_box.label(text="Simulation Timing", icon='TIME')
        timing_col = timing_box.column(align=True)
        timing_col.prop(props, "dt", text="Fixed Δt")

        toggle = timing_col.row(align=True)
        toggle.use_property_split = False
        toggle.prop(props, "enable_adaptive_dt", text="Adaptive Step", toggle=True)

        if props.enable_adaptive_dt:
            adaptive = timing_col.column(align=True)
            adaptive.label(text="Adaptive Window", icon='AUTO')
            adaptive.prop(props, "dt_min", text="Min Δt")
            adaptive.prop(props, "dt_max", text="Max Δt")
            adaptive.prop(props, "cfl_safety_factor", text="Safety Factor")

        timing_col.prop(props, "beta_max", text="β Max")

        solver_box = layout.box()
        solver_box.label(text="Solver Settings", icon='MOD_PHYSICS')
        solver_col = solver_box.column(align=True)

        newton = solver_col.column(align=True)
        newton.label(text="Newton", icon='SETTINGS')
        newton.prop(props, "min_newton_steps", text="Min Steps")
        newton.prop(props, "max_newton_steps", text="Max Steps")

        solver_col.separator()

        pcg = solver_col.column(align=True)
        pcg.label(text="PCG", icon='SETTINGS')
        pcg.prop(props, "pcg_tol", text="Tolerance")
        pcg.prop(props, "pcg_max_iters", text="Max Iterations")


class ANDO_PT_scene_setup_panel(Panel):
    """Panel guiding users through hybrid scene preparation."""

    bl_label = "Simulation Setup"
    bl_idname = "ANDO_PT_scene_setup_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Ando Physics'
    bl_parent_id = "ANDO_PT_main_panel"

    def draw(self, context):
        layout = _configure_layout(self.layout)
        deformable_count, rigid_count = _count_sim_objects(context)

        summary = layout.row(align=True)
        summary.label(text=f"Deformables: {deformable_count}", icon='MESH_GRID')
        summary.label(text=f"Rigid Colliders: {rigid_count}", icon='CUBE')

        obj = context.active_object
        if obj and obj.type == 'MESH':
            body_props = getattr(obj, "ando_barrier_body", None)
            box = layout.box()
            header = box.row(align=True)
            header.label(text="Active Mesh", icon='MESH_DATA')
            header.label(text=obj.name)
            if body_props:
                toggle = box.row(align=True)
                toggle.use_property_split = False
                toggle.prop(body_props, "enabled", text="Include in Simulation", toggle=True)
                if body_props.enabled:
                    role = box.row(align=True)
                    role.use_property_split = False
                    role.prop(body_props, "role", expand=True)
                    if body_props.role == 'RIGID':
                        box.prop(body_props, "rigid_density", text="Density")
                else:
                    info = box.row()
                    info.label(text="Mesh excluded from the solver.", icon='INFO')
            else:
                warning = box.row()
                warning.alert = True
                warning.label(text="Enable Ando properties for this mesh to configure roles.", icon='ERROR')
        else:
            layout.label(text="Select a mesh to configure its role.", icon='INFO')

        help_box = layout.box()
        help_box.label(text="Workflow Tips", icon='QUESTION')
        col = help_box.column(align=True)
        col.label(text="• Enable a deformable mesh (cloth/soft body).")
        col.label(text="• Mark rigid meshes as colliders.")
        col.label(text="• Launch the real-time preview to sync transforms.")


class ANDO_PT_contact_panel(Panel):
    """Contact settings panel"""
    bl_label = "Contact & Constraints"
    bl_idname = "ANDO_PT_contact_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Ando Physics'
    bl_parent_id = "ANDO_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = _configure_layout(self.layout)
        props = _get_scene_props(context)
        if props is None:
            layout.label(text="Scene properties unavailable", icon='ERROR')
            return

        if _active_backend(context) == _BACKEND_PPF:
            layout.label(text="Debug overlays are unavailable for the PPF backend.", icon='INFO')
            return
        col = layout.column(align=True)
        col.prop(props, "contact_gap_max", text="Contact Gap")
        col.prop(props, "wall_gap", text="Wall Gap")
        col.prop(props, "enable_ccd", text="Continuous Collision Detection")

        ground_box = layout.box()
        ground_toggle = ground_box.row(align=True)
        ground_toggle.use_property_split = False
        ground_toggle.prop(props, "enable_ground_plane", text="Ground Plane", toggle=True)
        if props.enable_ground_plane:
            ground_box.prop(props, "ground_plane_height", text="Height")

        layout.separator()
        layout.label(text="Add Constraints", icon='MOD_PHYSICS')
        ops = layout.row(align=True)
        ops.operator("ando.add_pin_constraint", text="Pin", icon='PINNED')
        ops.operator("ando.add_wall_constraint", text="Wall", icon='MESH_PLANE')

class ANDO_PT_friction_panel(Panel):
    """Friction settings panel"""
    bl_label = "Friction (Optional)"
    bl_idname = "ANDO_PT_friction_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Ando Physics'
    bl_parent_id = "ANDO_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw_header(self, context):
        props = _get_scene_props(context)
        if props is None:
            self.layout.label(text="", icon='ERROR')
            return
        layout = _configure_layout(self.layout)
        layout.use_property_split = False
        layout.prop(props, "enable_friction", text="")
    
    def draw(self, context):
        layout = _configure_layout(self.layout)
        props = _get_scene_props(context)
        if props is None:
            layout.label(text="Scene properties unavailable", icon='ERROR')
            return
        
        layout.enabled = props.enable_friction
        layout.prop(props, "friction_mu")
        layout.prop(props, "friction_epsilon")

class ANDO_PT_damping_panel(Panel):
    """Damping and restitution controls"""
    bl_label = "Damping & Restitution"
    bl_idname = "ANDO_PT_damping_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Ando Physics'
    bl_parent_id = "ANDO_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = _configure_layout(self.layout)
        props = _get_scene_props(context)
        if props is None:
            layout.label(text="Scene properties unavailable", icon='ERROR')
            return

        layout.prop(props, "velocity_damping")
        layout.prop(props, "contact_restitution")

class ANDO_PT_strain_limiting_panel(Panel):
    """Strain limiting settings panel"""
    bl_label = "Strain Limiting (Optional)"
    bl_idname = "ANDO_PT_strain_limiting_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Ando Physics'
    bl_parent_id = "ANDO_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw_header(self, context):
        props = _get_scene_props(context)
        if props is None:
            self.layout.label(text="", icon='ERROR')
            return
        layout = _configure_layout(self.layout)
        layout.use_property_split = False
        layout.prop(props, "enable_strain_limiting", text="")
    
    def draw(self, context):
        layout = _configure_layout(self.layout)
        props = _get_scene_props(context)
        if props is None:
            layout.label(text="Scene properties unavailable", icon='ERROR')
            return
        
        layout.enabled = props.enable_strain_limiting
        layout.prop(props, "strain_limit")
        layout.prop(props, "strain_tau")

class ANDO_PT_material_panel(Panel):
    """Material properties panel"""
    bl_label = "Material Properties"
    bl_idname = "ANDO_PT_material_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Ando Physics'
    bl_parent_id = "ANDO_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = _configure_layout(self.layout)
        props = _get_scene_props(context)
        if props is None:
            layout.label(text="Scene properties unavailable", icon='ERROR')
            return
        mat_props = getattr(props, "material_properties", None)
        if mat_props is None or not hasattr(mat_props, "rna_type"):
            layout.label(text="Material properties unavailable", icon='ERROR')
            layout.label(text="Try reloading the add-on.", icon='INFO')
            return
        
        active_obj = context.active_object
        if active_obj and active_obj.type == 'MESH':
            mat_box = layout.box()
            header = mat_box.row(align=True)
            header.label(text="Active Mesh", icon='MESH_DATA')
            header.label(text=active_obj.name)
            mat_box.prop(props, "material_preset", text="Preset")

            values = mat_box.column(align=True)
            values.prop(mat_props, "youngs_modulus", text="Young's Modulus")
            values.prop(mat_props, "poisson_ratio", text="Poisson Ratio")
            values.prop(mat_props, "density", text="Density")
            values.prop(mat_props, "thickness", text="Thickness")
        else:
            layout.label(text="Select a mesh object", icon='INFO')

class ANDO_PT_cache_panel(Panel):
    """Cache and baking panel"""
    bl_label = "Cache & Baking"
    bl_idname = "ANDO_PT_cache_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Ando Physics'
    bl_parent_id = "ANDO_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = _configure_layout(self.layout)
        props = _get_scene_props(context)
        if props is None:
            layout.label(text="Scene properties unavailable", icon='ERROR')
            return
        
        toggle = layout.row(align=True)
        toggle.use_property_split = False
        toggle.prop(props, "cache_enabled", text="Enable Cache", toggle=True)
        
        range_row = layout.row(align=True)
        range_row.prop(props, "cache_start", text="Start")
        range_row.prop(props, "cache_end", text="End")
        
        actions = layout.row(align=True)
        actions.enabled = props.cache_enabled
        actions.operator("ando.bake_simulation", text="Bake", icon='RENDER_ANIMATION')
        actions.operator("ando.reset_simulation", text="Clear", icon='FILE_REFRESH')

class ANDO_PT_realtime_panel(Panel):
    """Real-time preview panel"""
    bl_label = "Real-Time Preview"
    bl_idname = "ANDO_PT_realtime_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Ando Physics'
    bl_parent_id = "ANDO_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = _configure_layout(self.layout)
        props = _get_scene_props(context)
        if props is None:
            layout.label(text="Scene properties unavailable", icon='ERROR')
            row = layout.row()
            row.enabled = False
            row.operator("ando.init_realtime_simulation", text="Initialize", icon='PLAY')
            return

        backend = _active_backend(context)
        if backend == _BACKEND_PPF:
            _draw_ppf_session(layout)
            return

        _draw_ando_session(layout, context)

class ANDO_PT_debug_panel(Panel):
    """Debug visualization panel"""
    bl_label = "Debug & Statistics"
    bl_idname = "ANDO_PT_debug_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Ando Physics'
    bl_parent_id = "ANDO_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = _configure_layout(self.layout)
        props = _get_scene_props(context)
        if props is None:
            layout.label(text="Scene properties unavailable", icon='ERROR')
            return
        
        try:
            from . import operators, visualization
            sim_state = operators._sim_state

            # Visualization toggle
            box = layout.box()
            box.label(text="Visualization", icon='HIDE_OFF')
            
            vis_text = "Hide Overlays" if visualization.is_visualization_enabled() else "Show Overlays"
            vis_icon = 'HIDE_OFF' if visualization.is_visualization_enabled() else 'HIDE_ON'
            box.operator("ando.toggle_debug_visualization", text=vis_text, icon=vis_icon)
            
            if visualization.is_visualization_enabled():
                # Heatmap toggles
                col = box.column(align=True)
                col.prop(props, "show_gap_heatmap", text="Gap Heatmap", toggle=True)
                col.prop(props, "show_strain_overlay", text="Strain Overlay", toggle=True)

            rigid_count = sim_state['stats'].get('num_rigid_bodies', 0)
            if rigid_count:
                layout.label(text=f"Rigid bodies in solver: {rigid_count}", icon='CUBE')
                
                # Show legend only if heatmaps are off
                if not props.show_gap_heatmap and not props.show_strain_overlay:
                    box.separator()
                    box.label(text="Contact Legend:", icon='DOT')
                    box.label(text="  Red = Point-Triangle")
                    box.label(text="  Orange = Edge-Edge")
                    box.label(text="  Yellow = Wall")
                    box.label(text="  Blue = Pins")
                elif props.show_gap_heatmap:
                    box.separator()
                    box.label(text="Gap Heatmap Legend:", icon='DOT')
                    box.label(text="  Red = Contact (< 0.1mm)")
                    box.label(text="  Yellow = Close (< 0.3mm)")
                    box.label(text="  Green = Safe (> 1mm)")
                    box.prop(props, "gap_heatmap_range")
                elif props.show_strain_overlay:
                    box.separator()
                    box.label(text="Strain Legend:", icon='DOT')
                    box.label(text="  Blue = No stretch")
                    box.label(text="  Green = Mild stretch")
                    box.label(text="  Yellow = Moderate")
                    box.label(text="  Red = At limit")
            
            # Statistics
            if sim_state['initialized']:
                box = layout.box()
                box.label(text="Performance", icon='TIME')
                stats = sim_state['stats']
                
                col = box.column(align=True)
                col.label(text=f"Contacts: {stats['num_contacts']}")
                if stats.get('peak_contacts', 0):
                    col.label(text=f"Peak contacts: {stats['peak_contacts']}")
                col.label(text=f"Pins: {stats['num_pins']}")
                
                if stats['last_step_time'] > 0:
                    col.label(text=f"Step time: {stats['last_step_time']:.1f} ms")
                    fps = 1000.0 / stats['last_step_time'] if stats['last_step_time'] > 0 else 0
                    col.label(text=f"FPS: {fps:.1f}")

                counts = stats.get('contact_counts', {})
                if counts:
                    box.separator()
                    box.label(text="Contacts by Type", icon='OUTLINER_OB_GROUP_INSTANCE')
                    for ctype in sorted(counts.keys()):
                        current = counts.get(ctype, 0)
                        peak = stats.get('peak_contact_counts', {}).get(ctype, current)
                        box.label(text=f"{ctype}: {current} (peak {peak})")
                
                # Energy diagnostics
                box = layout.box()
                box.label(text="Energy & Conservation", icon='LIGHT_SUN')
                
                # Current energy values
                col = box.column(align=True)
                total_e = stats.get('total_energy', 0.0)
                kinetic_e = stats.get('kinetic_energy', 0.0)
                elastic_e = stats.get('elastic_energy', 0.0)
                
                col.label(text=f"Total: {total_e:.3e} J")
                col.label(text=f"Kinetic: {kinetic_e:.3e} J")
                col.label(text=f"Elastic: {elastic_e:.3e} J")
                
                # Energy drift warning
                drift_pct = stats.get('energy_drift_percent', 0.0)
                drift_abs = stats.get('energy_drift_absolute', 0.0)
                
                box.separator()
                row = box.row()
                if abs(drift_pct) > 10.0:
                    row.alert = True
                    row.label(text=f"Drift: {drift_pct:+.2f}% ⚠", icon='ERROR')
                elif abs(drift_pct) > 5.0:
                    row.label(text=f"Drift: {drift_pct:+.2f}% ⚡", icon='INFO')
                else:
                    row.label(text=f"Drift: {drift_pct:+.2f}% ✓")
                
                # Momentum conservation
                box.separator()
                lin_mom = stats.get('linear_momentum', [0, 0, 0])
                ang_mom = stats.get('angular_momentum', [0, 0, 0])
                lin_mag = (lin_mom[0]**2 + lin_mom[1]**2 + lin_mom[2]**2)**0.5
                ang_mag = (ang_mom[0]**2 + ang_mom[1]**2 + ang_mom[2]**2)**0.5
                
                col = box.column(align=True)
                col.label(text=f"Lin momentum: {lin_mag:.3e}")
                col.label(text=f"Ang momentum: {ang_mag:.3e}")
                col.label(text=f"Max velocity: {stats.get('max_velocity', 0.0):.2f} m/s")
                
                # Energy history visualization hint
                if len(stats.get('energy_history', [])) > 2:
                    box.separator()
                    box.label(text=f"History: {len(stats['energy_history'])} frames tracked")
                
                # Collision quality metrics
                box = layout.box()
                box.label(text="Collision Quality", icon='MESH_DATA')
                
                # Quality level with color coding
                quality_level = stats.get('collision_quality', 0)
                quality_desc = stats.get('collision_quality_desc', 'Unknown')
                
                row = box.row()
                if quality_level == 3:
                    row.alert = True
                    row.label(text=f"⚠ {quality_desc}", icon='ERROR')
                elif quality_level == 2:
                    row.label(text=f"⚡ {quality_desc}", icon='INFO')
                elif quality_level == 1:
                    row.label(text=f"✓ {quality_desc}")
                else:
                    row.label(text=f"✓ {quality_desc}")
                
                # Gap statistics
                box.separator()
                col = box.column(align=True)
                col.label(text="Gap Statistics:")
                min_gap = stats.get('min_gap', 0.0) * 1000  # Convert to mm
                max_gap = stats.get('max_gap', 0.0) * 1000
                avg_gap = stats.get('avg_gap', 0.0) * 1000
                col.label(text=f"  Min: {min_gap:.2f} mm")
                col.label(text=f"  Max: {max_gap:.2f} mm")
                col.label(text=f"  Avg: {avg_gap:.2f} mm")
                
                # Penetration detection
                num_pen = stats.get('num_penetrations', 0)
                if num_pen > 0:
                    box.separator()
                    row = box.row()
                    row.alert = True
                    max_pen = stats.get('max_penetration', 0.0) * 1000  # mm
                    row.label(text=f"⚠ {num_pen} penetrations", icon='ERROR')
                    col = box.column(align=True)
                    col.label(text=f"  Max depth: {max_pen:.3f} mm")
                    
                    if stats.get('has_tunneling', False):
                        row = box.row()
                        row.alert = True
                        row.label(text="  TUNNELING DETECTED", icon='ERROR')
                
                # CCD effectiveness (if enabled)
                if stats.get('ccd_effectiveness', 0.0) > 0:
                    box.separator()
                    ccd_eff = stats.get('ccd_effectiveness', 0.0)
                    box.label(text=f"CCD: {ccd_eff:.1f}% effectiveness")
                
                # Relative velocity
                max_rel_v = stats.get('max_relative_velocity', 0.0)
                if max_rel_v > 0.01:  # Only show if significant
                    box.separator()
                    box.label(text=f"Max impact: {max_rel_v:.2f} m/s")
                    
        except ImportError:
            layout.label(text="Core module not loaded", icon='ERROR')

classes = (
    ANDO_PT_main_panel,
    ANDO_PT_scene_setup_panel,
    ANDO_PT_contact_panel,
    ANDO_PT_friction_panel,
    ANDO_PT_damping_panel,
    ANDO_PT_strain_limiting_panel,
    ANDO_PT_material_panel,
    ANDO_PT_cache_panel,
    ANDO_PT_realtime_panel,
    ANDO_PT_debug_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
