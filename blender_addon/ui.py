import logging
from pathlib import Path

import bpy
from bpy.types import Panel

from ._core_loader import get_core_module

_LOGGER = logging.getLogger(__name__)
_LOGGED_REALTIME_CORE_FAILURE = False
_LOGGED_OPERATOR_IMPORT_FAILURE = False


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


class ANDO_PT_main_panel(Panel):
    """Main panel for Ando Barrier Physics"""
    bl_label = "Ando Barrier Physics"
    bl_idname = "ANDO_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Ando Physics'
    
    def draw(self, context):
        layout = self.layout
        props = _get_scene_props(context)

        # Check if core module is available
        core_module = get_core_module(context="UI status check")
        if core_module is None:
            layout.label(text="Core module not loaded", icon='ERROR')
            layout.label(text="Build C++ extension first")
            return

        try:
            layout.label(text=core_module.version(), icon='INFO')
        except AttributeError:
            layout.label(text="Core module loaded", icon='INFO')
        
        if props is None:
            layout.label(text="Scene properties unavailable", icon='ERROR')
            layout.label(text="Re-enable the add-on or reopen the file.", icon='INFO')
            return
        
        # Time stepping
        box = layout.box()
        box.label(text="Time Integration", icon='TIME')
        box.prop(props, "dt")
        
        # Adaptive timestepping
        col = box.column(align=True)
        col.prop(props, "enable_adaptive_dt", toggle=True)
        if props.enable_adaptive_dt:
            sub = col.box()
            sub.label(text="CFL Parameters:", icon='AUTO')
            sub.prop(props, "dt_min", text="Min Δt")
            sub.prop(props, "dt_max", text="Max Δt")
            sub.prop(props, "cfl_safety_factor", text="Safety Factor")
        
        box.prop(props, "beta_max")
        
        # Newton solver
        box = layout.box()
        box.label(text="Newton Solver", icon='SETTINGS')
        box.prop(props, "min_newton_steps")
        box.prop(props, "max_newton_steps")
        
        # PCG solver
        box = layout.box()
        box.label(text="PCG Solver", icon='SETTINGS')
        box.prop(props, "pcg_tol")
        box.prop(props, "pcg_max_iters")


class ANDO_PT_scene_setup_panel(Panel):
    """Panel guiding users through hybrid scene preparation."""

    bl_label = "Simulation Setup"
    bl_idname = "ANDO_PT_scene_setup_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Ando Physics'
    bl_parent_id = "ANDO_PT_main_panel"

    def draw(self, context):
        layout = self.layout
        deformable_count, rigid_count = _count_sim_objects(context)

        summary = layout.row(align=True)
        summary.label(text=f"Deformables: {deformable_count}", icon='MESH_GRID')
        summary.label(text=f"Rigid Colliders: {rigid_count}", icon='CUBE')

        obj = context.active_object
        if obj and obj.type == 'MESH':
            body_props = getattr(obj, "ando_barrier_body", None)
            box = layout.box()
            box.label(text=f"Active Mesh: {obj.name}", icon='MESH_DATA')
            if body_props:
                box.prop(body_props, "enabled", text="Include in Ando Simulation")
                if body_props.enabled:
                    box.prop(body_props, "role", expand=True)
                    if body_props.role == 'RIGID':
                        box.prop(body_props, "rigid_density")
                        box.label(text="Rigid colliders follow the solver as a single solid body.", icon='INFO')
                    else:
                        box.label(text="Deformables use the material settings below.", icon='INFO')
                else:
                    box.label(text="Disabled meshes are ignored by the solver.", icon='INFO')
            else:
                box.label(text="Enable the add-on to configure simulation roles.", icon='ERROR')
        else:
            layout.label(text="Select a mesh to configure its role.", icon='INFO')

        help_box = layout.box()
        help_box.label(text="Hybrid Workflow", icon='QUESTION')
        col = help_box.column(align=True)
        col.label(text="1. Enable at least one deformable surface (cloth/soft body).")
        col.label(text="2. Mark rigid meshes as colliders to catch and push the cloth.")
        col.label(text="3. Initialize the real-time preview to sync rigid colliders.")
        col.label(text="   (Rigid transforms are written back every frame.)")


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
        layout = self.layout
        props = _get_scene_props(context)
        if props is None:
            layout.label(text="Scene properties unavailable", icon='ERROR')
            return
        
        layout.prop(props, "contact_gap_max")
        layout.prop(props, "wall_gap")
        layout.prop(props, "enable_ccd")
        
        # Ground plane
        layout.separator()
        box = layout.box()
        box.prop(props, "enable_ground_plane")
        if props.enable_ground_plane:
            box.prop(props, "ground_plane_height")
        
        # Constraint operators
        layout.separator()
        layout.label(text="Add Constraints:")
        layout.operator("ando.add_pin_constraint", icon='PINNED')
        layout.operator("ando.add_wall_constraint", icon='MESH_PLANE')

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
        self.layout.prop(props, "enable_friction", text="")
    
    def draw(self, context):
        layout = self.layout
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
        layout = self.layout
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
        self.layout.prop(props, "enable_strain_limiting", text="")
    
    def draw(self, context):
        layout = self.layout
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
        layout = self.layout
        props = _get_scene_props(context)
        if props is None:
            layout.label(text="Scene properties unavailable", icon='ERROR')
            return
        mat_props = getattr(props, "material_properties", None)
        if mat_props is None or not hasattr(mat_props, "rna_type"):
            layout.label(text="Material properties unavailable", icon='ERROR')
            layout.label(text="Try reloading the add-on.", icon='INFO')
            return
        
        if context.active_object and context.active_object.type == 'MESH':
            layout.label(text="Material for active mesh:")
            layout.prop(props, "material_preset", text="Preset")
            layout.separator()
            layout.prop(mat_props, "youngs_modulus")
            layout.prop(mat_props, "poisson_ratio")
            layout.prop(mat_props, "density")
            layout.prop(mat_props, "thickness")
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
        layout = self.layout
        props = _get_scene_props(context)
        if props is None:
            layout.label(text="Scene properties unavailable", icon='ERROR')
            return
        
        layout.prop(props, "cache_enabled")
        
        row = layout.row(align=True)
        row.prop(props, "cache_start")
        row.prop(props, "cache_end")
        
        layout.separator()
        layout.operator("ando.bake_simulation", icon='RENDER_ANIMATION')
        layout.operator("ando.reset_simulation", icon='FILE_REFRESH')

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
        layout = self.layout
        props = _get_scene_props(context)
        if props is None:
            layout.label(text="Scene properties unavailable", icon='ERROR')
            row = layout.row()
            row.enabled = False
            row.operator("ando.init_realtime_simulation", text="Initialize", icon='PLAY')
            return
        
        core_module = get_core_module(context="Real-time preview panel")
        core_hint = _core_path_hint(core_module)

        global _LOGGED_REALTIME_CORE_FAILURE  # pylint: disable=global-statement
        global _LOGGED_OPERATOR_IMPORT_FAILURE  # pylint: disable=global-statement

        if core_module is None:
            layout.label(text="Core module unavailable; real-time preview disabled.", icon='ERROR')
            layout.label(text="See console for resolved path hint.", icon='INFO')
            row = layout.row()
            row.enabled = False
            row.operator("ando.init_realtime_simulation", text="Initialize", icon='PLAY')

            if not _LOGGED_REALTIME_CORE_FAILURE:
                _LOGGER.error(
                    "Real-time preview initialization blocked: ando_barrier_core not found. Resolved search path: %s",
                    core_hint,
                )
                _LOGGED_REALTIME_CORE_FAILURE = True
            return

        try:
            from . import operators
        except ImportError as exc:
            layout.label(text="Failed to load real-time controls.", icon='ERROR')
            layout.label(text="See console for diagnostics.", icon='INFO')
            row = layout.row()
            row.enabled = False
            row.operator("ando.init_realtime_simulation", text="Initialize", icon='PLAY')

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
            layout.label(text=f"Frame: {sim_state['frame']}", icon='TIME')

            rigid_objs = [obj for obj in sim_state.get('rigid_objects', []) if obj]
            if rigid_objs:
                names = ", ".join(obj.name for obj in rigid_objs[:2])
                if len(rigid_objs) > 2:
                    names += ", …"
                layout.label(text=f"Rigid colliders: {names}", icon='CUBE')
            elif _count_sim_objects(context)[1] > 0:
                layout.label(text="Rigid colliders configured; reinitialize to sync.", icon='INFO')

            # Play/pause button
            row = layout.row(align=True)
            play_icon = 'PAUSE' if sim_state['playing'] else 'PLAY'
            play_text = "Pause" if sim_state['playing'] else "Play"
            row.operator("ando.toggle_play_simulation", text=play_text, icon=play_icon)
            
            # Step button
            row = layout.row(align=True)
            row.operator("ando.step_simulation", text="Step", icon='FRAME_NEXT')
            row.operator("ando.reset_realtime_simulation", text="Reset", icon='FILE_REFRESH')
            
            # Hot-reload parameter update
            layout.separator()
            box = layout.box()
            box.label(text="Parameter Control", icon='SETTINGS')
            box.operator("ando.update_parameters", text="Apply Changes", icon='FILE_REFRESH')
            box.label(text="Update materials/settings", icon='INFO')
            box.label(text="without restarting sim")
        else:
            layout.label(text="Not initialized", icon='INFO')
            layout.operator("ando.init_realtime_simulation", text="Initialize", icon='PLAY')

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
        layout = self.layout
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
