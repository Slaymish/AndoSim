import bpy
from bpy.types import Panel

class ANDO_PT_main_panel(Panel):
    """Main panel for Ando Barrier Physics"""
    bl_label = "Ando Barrier Physics"
    bl_idname = "ANDO_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Ando Physics'
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.ando_barrier
        
        # Check if core module is available
        try:
            import ando_barrier_core as abc
            layout.label(text=abc.version(), icon='INFO')
        except ImportError:
            layout.label(text="Core module not loaded", icon='ERROR')
            layout.label(text="Build C++ extension first")
            return
        
        # Time stepping
        box = layout.box()
        box.label(text="Time Integration", icon='TIME')
        box.prop(props, "dt")
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
        props = context.scene.ando_barrier
        
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
        self.layout.prop(context.scene.ando_barrier, "enable_friction", text="")
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.ando_barrier
        
        layout.enabled = props.enable_friction
        layout.prop(props, "friction_mu")
        layout.prop(props, "friction_epsilon")

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
        self.layout.prop(context.scene.ando_barrier, "enable_strain_limiting", text="")
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.ando_barrier
        
        layout.enabled = props.enable_strain_limiting
        layout.prop(props, "strain_limit")

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
        props = context.scene.ando_barrier
        mat_props = props.material_properties
        
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
        props = context.scene.ando_barrier
        
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
        
        # Import to check simulation state
        try:
            from . import operators
            sim_state = operators._sim_state
            
            if sim_state['initialized']:
                layout.label(text=f"Frame: {sim_state['frame']}", icon='TIME')
                
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
                
        except ImportError:
            layout.label(text="Core module not loaded", icon='ERROR')

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
                box.label(text="Red = Contacts", icon='DOT')
                box.label(text="Green = Normals", icon='DOT')
                box.label(text="Blue = Pins", icon='DOT')
            
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
                    
        except ImportError:
            layout.label(text="Core module not loaded", icon='ERROR')

classes = (
    ANDO_PT_main_panel,
    ANDO_PT_contact_panel,
    ANDO_PT_friction_panel,
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
