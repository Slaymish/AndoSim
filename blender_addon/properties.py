import bpy
from bpy.types import PropertyGroup
from bpy.props import (
    FloatProperty,
    IntProperty,
    BoolProperty,
    EnumProperty,
    PointerProperty,
)

class AndoBarrierMaterialProperties(PropertyGroup):
    """Material properties for Ando Barrier simulation"""
    
    youngs_modulus: FloatProperty(
        name="Young's Modulus (E)",
        description="Young's modulus in Pa",
        default=1e6,
        min=1e3,
        max=1e9,
        unit='NONE',
    )
    
    poisson_ratio: FloatProperty(
        name="Poisson Ratio (ν)",
        description="Poisson's ratio",
        default=0.3,
        min=0.0,
        max=0.49,
    )
    
    density: FloatProperty(
        name="Density (ρ)",
        description="Material density in kg/m³",
        default=1000.0,
        min=1.0,
        max=10000.0,
    )
    
    thickness: FloatProperty(
        name="Thickness",
        description="Shell thickness in meters",
        default=0.001,
        min=0.0001,
        max=0.1,
        unit='LENGTH',
    )

class AndoBarrierSceneProperties(PropertyGroup):
    """Scene-level simulation properties"""
    
    # Time stepping
    dt: FloatProperty(
        name="Time Step (Δt)",
        description="Time step in milliseconds",
        default=2.0,
        min=0.1,
        max=10.0,
        unit='NONE',
    )
    
    beta_max: FloatProperty(
        name="Beta Max",
        description="Maximum beta accumulation for integrator",
        default=0.25,
        min=0.01,
        max=1.0,
    )
    
    # Newton solver
    min_newton_steps: IntProperty(
        name="Min Newton Steps",
        description="Minimum Newton iterations per step",
        default=2,
        min=1,
        max=32,
    )
    
    max_newton_steps: IntProperty(
        name="Max Newton Steps",
        description="Maximum Newton iterations per step",
        default=8,
        min=1,
        max=32,
    )
    
    # PCG solver
    pcg_tol: FloatProperty(
        name="PCG Tolerance",
        description="Relative L∞ tolerance for PCG",
        default=1e-3,
        min=1e-6,
        max=1e-1,
    )
    
    pcg_max_iters: IntProperty(
        name="PCG Max Iterations",
        description="Maximum PCG iterations",
        default=1000,
        min=10,
        max=10000,
    )
    
    # Contact parameters
    contact_gap_max: FloatProperty(
        name="Contact Gap Max (ḡ)",
        description="Maximum gap for contact barrier in meters",
        default=0.001,
        min=0.0001,
        max=0.01,
        unit='LENGTH',
    )
    
    wall_gap: FloatProperty(
        name="Wall Gap",
        description="Gap for wall constraints in meters",
        default=0.001,
        min=0.0001,
        max=0.01,
        unit='LENGTH',
    )
    
    enable_ccd: BoolProperty(
        name="Enable CCD",
        description="Enable continuous collision detection in line search",
        default=True,
    )
    
    # Friction (optional)
    enable_friction: BoolProperty(
        name="Enable Friction",
        description="Enable friction constraints",
        default=False,
    )
    
    friction_mu: FloatProperty(
        name="Friction μ",
        description="Friction coefficient",
        default=0.1,
        min=0.0,
        max=1.0,
    )
    
    friction_epsilon: FloatProperty(
        name="Friction ε",
        description="Friction epsilon in meters",
        default=1e-5,
        min=1e-6,
        max=1e-3,
        unit='LENGTH',
    )
    
    # Strain limiting (optional)
    enable_strain_limiting: BoolProperty(
        name="Enable Strain Limiting",
        description="Enable strain limiting constraints",
        default=False,
    )
    
    strain_limit: FloatProperty(
        name="Strain Limit %",
        description="Maximum strain as percentage (e.g., 5 for 5%)",
        default=5.0,
        min=0.1,
        max=50.0,
    )
    
    # Cache settings
    cache_enabled: BoolProperty(
        name="Enable Caching",
        description="Cache simulation results",
        default=True,
    )
    
    cache_start: IntProperty(
        name="Cache Start Frame",
        description="First frame to cache",
        default=1,
    )
    
    cache_end: IntProperty(
        name="Cache End Frame",
        description="Last frame to cache",
        default=250,
    )

classes = (
    AndoBarrierMaterialProperties,
    AndoBarrierSceneProperties,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Object.ando_barrier_material = PointerProperty(type=AndoBarrierMaterialProperties)
    bpy.types.Scene.ando_barrier = PointerProperty(type=AndoBarrierSceneProperties)

def unregister():
    del bpy.types.Scene.ando_barrier
    del bpy.types.Object.ando_barrier_material
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
