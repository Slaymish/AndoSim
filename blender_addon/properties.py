import bpy
from bpy.types import PropertyGroup
from bpy.props import (
    FloatProperty,
    IntProperty,
    BoolProperty,
    EnumProperty,
    PointerProperty,
)

from typing import Optional

# -----------------------------------------------------------------------------
# Material preset definitions
# -----------------------------------------------------------------------------

_MATERIAL_PRESET_DATA = {
    "CLOTH": {
        "label": "Cloth",
        "description": "Heavy cloth tuned for draping demos",
        "material": {
            "youngs_modulus": 3.0e5,
            "poisson_ratio": 0.35,
            "density": 1100.0,
            "thickness": 0.003,
        },
        "scene": {
            "dt": 3.0,
            "beta_max": 0.25,
            "enable_friction": True,
            "friction_mu": 0.4,
            "friction_epsilon": 5e-5,
            "contact_gap_max": 5e-4,
            "wall_gap": 5e-4,
            "enable_strain_limiting": True,
            "strain_limit": 8.0,
            "strain_tau": 0.08,
            "velocity_damping": 0.05,
            "contact_restitution": 0.15,
        },
    },
    "RUBBER": {
        "label": "Rubber",
        "description": "Stretchy rubber sheet with high friction",
        "material": {
            "youngs_modulus": 2.5e6,
            "poisson_ratio": 0.45,
            "density": 1200.0,
            "thickness": 0.004,
        },
        "scene": {
            "dt": 2.0,
            "beta_max": 0.2,
            "enable_friction": True,
            "friction_mu": 0.8,
            "friction_epsilon": 8e-5,
            "contact_gap_max": 3e-4,
            "wall_gap": 3e-4,
            "enable_strain_limiting": False,
            "velocity_damping": 0.03,
            "contact_restitution": 0.4,
        },
    },
    "METAL": {
        "label": "Metal",
        "description": "Thin, stiff metal panel",
        "material": {
            "youngs_modulus": 5.0e8,
            "poisson_ratio": 0.3,
            "density": 7800.0,
            "thickness": 0.002,
        },
        "scene": {
            "dt": 1.5,
            "beta_max": 0.15,
            "enable_friction": True,
            "friction_mu": 0.3,
            "friction_epsilon": 5e-5,
            "contact_gap_max": 2e-4,
            "wall_gap": 2e-4,
            "enable_strain_limiting": False,
            "velocity_damping": 0.02,
            "contact_restitution": 0.6,
        },
    },
    "JELLY": {
        "label": "Jelly",
        "description": "Soft, bouncy jelly block",
        "material": {
            "youngs_modulus": 5.0e4,
            "poisson_ratio": 0.45,
            "density": 1050.0,
            "thickness": 0.01,
        },
        "scene": {
            "dt": 4.0,
            "beta_max": 0.3,
            "enable_friction": True,
            "friction_mu": 0.5,
            "friction_epsilon": 1.5e-4,
            "contact_gap_max": 7e-4,
            "wall_gap": 7e-4,
            "enable_strain_limiting": True,
            "strain_limit": 15.0,
            "strain_tau": 0.12,
            "velocity_damping": 0.08,
            "contact_restitution": 0.35,
        },
    },
    "LEATHER": {
        "label": "Leather",
        "description": "Thick leather for jackets and furniture",
        "material": {
            "youngs_modulus": 5.0e6,
            "poisson_ratio": 0.4,
            "density": 950.0,
            "thickness": 0.002,
        },
        "scene": {
            "dt": 2.5,
            "beta_max": 0.22,
            "enable_friction": True,
            "friction_mu": 0.6,
            "friction_epsilon": 6e-5,
            "contact_gap_max": 4e-4,
            "wall_gap": 4e-4,
            "enable_strain_limiting": True,
            "strain_limit": 5.0,
            "strain_tau": 0.05,
            "velocity_damping": 0.05,
            "contact_restitution": 0.2,
        },
    },
    "SILK": {
        "label": "Silk",
        "description": "Lightweight, smooth silk fabric for dresses",
        "material": {
            "youngs_modulus": 5.0e5,
            "poisson_ratio": 0.35,
            "density": 1300.0,
            "thickness": 0.0003,
        },
        "scene": {
            "dt": 2.0,
            "beta_max": 0.25,
            "enable_friction": True,
            "friction_mu": 0.2,
            "friction_epsilon": 4e-5,
            "contact_gap_max": 3e-4,
            "wall_gap": 3e-4,
            "enable_strain_limiting": True,
            "strain_limit": 6.0,
            "strain_tau": 0.06,
            "velocity_damping": 0.03,
            "contact_restitution": 0.25,
        },
    },
    "CANVAS": {
        "label": "Canvas",
        "description": "Heavy canvas for tents and sails",
        "material": {
            "youngs_modulus": 2.0e6,
            "poisson_ratio": 0.3,
            "density": 1400.0,
            "thickness": 0.0015,
        },
        "scene": {
            "dt": 2.5,
            "beta_max": 0.2,
            "enable_friction": True,
            "friction_mu": 0.5,
            "friction_epsilon": 6e-5,
            "contact_gap_max": 4e-4,
            "wall_gap": 4e-4,
            "enable_strain_limiting": True,
            "strain_limit": 4.0,
            "strain_tau": 0.04,
            "velocity_damping": 0.06,
            "contact_restitution": 0.15,
        },
    },
    "FOAM": {
        "label": "Foam",
        "description": "Soft foam padding for cushions",
        "material": {
            "youngs_modulus": 5.0e4,
            "poisson_ratio": 0.45,
            "density": 200.0,
            "thickness": 0.01,
        },
        "scene": {
            "dt": 3.5,
            "beta_max": 0.28,
            "enable_friction": True,
            "friction_mu": 0.7,
            "friction_epsilon": 1.2e-4,
            "contact_gap_max": 8e-4,
            "wall_gap": 8e-4,
            "enable_strain_limiting": True,
            "strain_limit": 20.0,
            "strain_tau": 0.15,
            "velocity_damping": 0.12,
            "contact_restitution": 0.1,
        },
    },
    "PLASTIC": {
        "label": "Plastic",
        "description": "Stiff plastic sheet for tarps and bags",
        "material": {
            "youngs_modulus": 1.0e9,
            "poisson_ratio": 0.35,
            "density": 1200.0,
            "thickness": 0.001,
        },
        "scene": {
            "dt": 1.8,
            "beta_max": 0.18,
            "enable_friction": True,
            "friction_mu": 0.4,
            "friction_epsilon": 5e-5,
            "contact_gap_max": 2.5e-4,
            "wall_gap": 2.5e-4,
            "enable_strain_limiting": False,
            "velocity_damping": 0.04,
            "contact_restitution": 0.3,
        },
    },
}

_MATERIAL_PRESET_ITEMS = [
    (key, data["label"], data["description"], idx)
    for idx, (key, data) in enumerate(_MATERIAL_PRESET_DATA.items())
]
_MATERIAL_PRESET_ITEMS.append(("CUSTOM", "Custom", "User-defined material parameters", len(_MATERIAL_PRESET_ITEMS)))

_PRESET_LOCK: set[int] = set()


def _lock_handle(obj: Optional[PropertyGroup]) -> Optional[int]:
    """Return a stable handle for RNA property group instances."""
    if obj is None:
        return None
    try:
        return obj.as_pointer()
    except AttributeError:  # pragma: no cover - defensive
        return None


def _is_preset_locked(obj: Optional[PropertyGroup]) -> bool:
    """Check whether the property group is currently applying a preset."""
    handle = _lock_handle(obj)
    return handle is not None and handle in _PRESET_LOCK


def _mark_material_custom(self, _context):
    """Mark the owning scene preset as custom when the user edits material parameters."""
    scene = getattr(self, "id_data", None)
    if isinstance(scene, bpy.types.Scene):
        props = getattr(scene, "ando_barrier", None)
        if props and not _is_preset_locked(props) and props.material_preset != "CUSTOM":
            props.material_preset = "CUSTOM"


def _mark_scene_custom(self, _context):
    """Mark preset as custom when a scene parameter tied to presets is edited."""
    if _is_preset_locked(self):
        return
    if self.material_preset != "CUSTOM":
        self.material_preset = "CUSTOM"


def _apply_material_preset(self, _context):
    """Apply preset values to material and scene properties."""
    if getattr(self, "_applying_preset", False):
        return
    preset_key = self.material_preset
    if preset_key == "CUSTOM":
        return
    preset = _MATERIAL_PRESET_DATA.get(preset_key)
    if not preset:
        return
    handle = _lock_handle(self)
    if handle is not None:
        _PRESET_LOCK.add(handle)
    try:
        mat_props = self.material_properties
        for attr, value in preset["material"].items():
            if hasattr(mat_props, attr):
                setattr(mat_props, attr, value)
        for attr, value in preset["scene"].items():
            if hasattr(self, attr):
                setattr(self, attr, value)
    finally:
        if handle is not None:
            _PRESET_LOCK.discard(handle)

class AndoBarrierMaterialProperties(PropertyGroup):
    """Material properties for Ando Barrier simulation"""
    
    youngs_modulus: FloatProperty(
        name="Young's Modulus (E)",
        description="Young's modulus in Pa",
        default=3.0e5,
        min=1e3,
        max=1e9,
        unit='NONE',
        update=_mark_material_custom,
    )
    
    poisson_ratio: FloatProperty(
        name="Poisson Ratio (ν)",
        description="Poisson's ratio",
        default=0.35,
        min=0.0,
        max=0.49,
        update=_mark_material_custom,
    )
    
    density: FloatProperty(
        name="Density (ρ)",
        description="Material density in kg/m³",
        default=1100.0,
        min=1.0,
        max=10000.0,
        update=_mark_material_custom,
    )
    
    thickness: FloatProperty(
        name="Thickness",
        description="Shell thickness in meters",
        default=0.003,
        min=0.0001,
        max=0.1,
        unit='LENGTH',
        update=_mark_material_custom,
    )

class AndoBarrierSceneProperties(PropertyGroup):
    """Scene-level simulation properties"""
    
    material_preset: EnumProperty(
        name="Material Preset",
        description="Apply tuned material parameter presets",
        items=_MATERIAL_PRESET_ITEMS,
        default="CLOTH",
        update=_apply_material_preset,
    )
    
    # Time stepping
    dt: FloatProperty(
        name="Time Step (Δt)",
        description="Time step in milliseconds",
        default=3.0,
        min=0.1,
        max=10.0,
        unit='NONE',
        update=_mark_scene_custom,
    )
    
    # Adaptive timestepping
    enable_adaptive_dt: BoolProperty(
        name="Enable Adaptive Timestep",
        description="Dynamically adjust timestep based on CFL condition",
        default=False,
    )
    
    dt_min: FloatProperty(
        name="Min Δt",
        description="Minimum timestep in milliseconds (stability floor)",
        default=0.1,
        min=0.01,
        max=5.0,
        unit='NONE',
    )
    
    dt_max: FloatProperty(
        name="Max Δt",
        description="Maximum timestep in milliseconds (for settled cloth)",
        default=10.0,
        min=1.0,
        max=50.0,
        unit='NONE',
    )
    
    cfl_safety_factor: FloatProperty(
        name="CFL Safety Factor",
        description="CFL safety factor (0.5 = conservative, 1.0 = aggressive)",
        default=0.5,
        min=0.1,
        max=1.0,
    )
    
    beta_max: FloatProperty(
        name="Beta Max",
        description="Maximum beta accumulation for integrator",
        default=0.25,
        min=0.01,
        max=1.0,
        update=_mark_scene_custom,
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
        default=5e-4,
        min=0.0001,
        max=0.01,
        unit='LENGTH',
        update=_mark_scene_custom,
    )
    
    wall_gap: FloatProperty(
        name="Wall Gap",
        description="Gap for wall constraints in meters",
        default=5e-4,
        min=0.0001,
        max=0.01,
        unit='LENGTH',
        update=_mark_scene_custom,
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
        default=True,
        update=_mark_scene_custom,
    )
    
    friction_mu: FloatProperty(
        name="Friction μ",
        description="Friction coefficient",
        default=0.4,
        min=0.0,
        max=1.0,
        update=_mark_scene_custom,
    )
    
    friction_epsilon: FloatProperty(
        name="Friction ε",
        description="Friction epsilon in meters",
        default=5e-5,
        min=1e-6,
        max=1e-3,
        unit='LENGTH',
        update=_mark_scene_custom,
    )

    # Damping & restitution
    velocity_damping: FloatProperty(
        name="Velocity Damping",
        description="Fraction of velocity removed each step (0 disables damping)",
        default=0.05,
        min=0.0,
        max=0.99,
        update=_mark_scene_custom,
    )

    contact_restitution: FloatProperty(
        name="Restitution",
        description="Bounce factor for contacts (0=inelastic, 1=perfectly elastic)",
        default=0.15,
        min=0.0,
        max=1.0,
        update=_mark_scene_custom,
    )

    # Strain limiting (optional)
    enable_strain_limiting: BoolProperty(
        name="Enable Strain Limiting",
        description="Enable strain limiting constraints",
        default=True,
        update=_mark_scene_custom,
    )

    strain_limit: FloatProperty(
        name="Strain Limit %",
        description="Maximum strain as percentage (e.g., 5 for 5%)",
        default=8.0,
        min=0.1,
        max=50.0,
        update=_mark_scene_custom,
    )

    strain_tau: FloatProperty(
        name="Strain τ",
        description="Strain tau parameter (usually equals strain epsilon)",
        default=0.08,
        min=0.001,
        max=0.5,
        update=_mark_scene_custom,
    )

    # Ground plane
    enable_ground_plane: BoolProperty(
        name="Enable Ground Plane",
        description="Add a ground plane collision constraint",
        default=True,
    )

    ground_plane_height: FloatProperty(
        name="Ground Height",
        description="Height of ground plane",
        default=0.0,
        unit='LENGTH',
    )

    # Visualization settings
    show_gap_heatmap: BoolProperty(
        name="Show Gap Heatmap",
        description="Display color-coded contact gap distances (red=contact, yellow=close, green=safe)",
        default=False,
    )

    show_strain_overlay: BoolProperty(
        name="Show Strain Overlay",
        description="Display color-coded strain magnitude (blue=no stretch, green=mild, yellow=moderate, red=limit)",
        default=False,
    )

    gap_heatmap_range: FloatProperty(
        name="Gap Range",
        description="Maximum gap distance for color mapping (meters)",
        default=0.001,
        min=0.0001,
        max=0.01,
        unit='LENGTH',
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

    # Material properties (nested)
    material_properties: PointerProperty(
        type=AndoBarrierMaterialProperties,
        name="Material",
        description="Material properties for this simulation",
    )


class AndoBarrierObjectProperties(PropertyGroup):
    """Per-object settings describing how meshes participate in the solver."""

    enabled: BoolProperty(
        name="Include in Ando Simulation",
        description="Enable to have this mesh participate in the Ando solver",
        default=False,
    )

    role: EnumProperty(
        name="Simulation Role",
        description="How this mesh is treated by the hybrid solver",
        items=(
            (
                'DEFORMABLE',
                "Deformable Surface",
                "Simulate as cloth/soft body using barrier-based elasticity",
            ),
            (
                'RIGID',
                "Rigid Collider",
                "Treat as a rigid obstacle that can collide with deformables",
            ),
        ),
        default='DEFORMABLE',
    )

    rigid_density: FloatProperty(
        name="Rigid Density",
        description=(
            "Approximate mass density used for rigid body response. Higher values "
            "make the collider harder to move when in hybrid mode."
        ),
        default=2500.0,
        min=10.0,
        max=20000.0,
        unit='NONE',
    )

classes = (
    AndoBarrierMaterialProperties,
    AndoBarrierSceneProperties,
    AndoBarrierObjectProperties,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.ando_barrier = PointerProperty(type=AndoBarrierSceneProperties)
    bpy.types.Object.ando_barrier_body = PointerProperty(type=AndoBarrierObjectProperties)


def unregister():
    del bpy.types.Scene.ando_barrier
    del bpy.types.Object.ando_barrier_body

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
