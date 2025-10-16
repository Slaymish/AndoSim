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
        
        # Constraint operators
        layout.separator()
        layout.operator("ando.add_pin_constraint")
        layout.operator("ando.add_wall_constraint")

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
        obj = context.active_object
        
        if obj and obj.type == 'MESH':
            mat_props = obj.ando_barrier_material
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

classes = (
    ANDO_PT_main_panel,
    ANDO_PT_contact_panel,
    ANDO_PT_friction_panel,
    ANDO_PT_strain_limiting_panel,
    ANDO_PT_material_panel,
    ANDO_PT_cache_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
