bl_info = {
    "name": "Ando Barrier Physics",
    "author": "BlenderSim Project",
    "version": (1, 0, 3),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Ando Physics",
    "description": "Cubic Barrier with Elasticity-Inclusive Dynamic Stiffness (Ando 2024)",
    "category": "Physics",
}

import bpy

from ._core_loader import get_core_module

_CORE = get_core_module(context="Add-on initialisation")
CORE_AVAILABLE = _CORE is not None

if CORE_AVAILABLE:
    try:
        print(f"Loaded {_CORE.version()}")
    except AttributeError:
        print("Loaded ando_barrier_core module (version unavailable)")
else:
    print("Warning: ando_barrier_core could not be imported during add-on initialisation")

from . import ui
from . import operators
from . import properties
from . import parameter_update

class AndoPrefs(bpy.types.AddonPreferences):
    bl_idname = __package__

    solver_backend: bpy.props.EnumProperty(
        name="Solver backend",
        items=[("ANDO", "Ando Core", ""), ("PPF", "PPF Contact Solver", "")],
        default="ANDO",
    )

    def draw(self, ctx):
        layout = self.layout
        layout.prop(self, "solver_backend")

def get_backend(ctx):
    try:
        addon = ctx.preferences.addons.get(__package__)
    except AttributeError:
        return "ANDO"
    if not addon:
        return "ANDO"
    return getattr(addon.preferences, "solver_backend", "ANDO")


def register():
    bpy.utils.register_class(AndoPrefs)
    properties.register()
    ui.register()
    operators.register()
    parameter_update.register()
    print("Ando Barrier Physics add-on registered")

def unregister():
    bpy.utils.unregister_class(AndoPrefs)
    parameter_update.unregister()
    operators.unregister()
    ui.unregister()
    properties.unregister()
    print("Ando Barrier Physics add-on unregistered")

if __name__ == "__main__":
    register()
