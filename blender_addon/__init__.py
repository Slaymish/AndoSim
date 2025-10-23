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

def register():
    properties.register()
    ui.register()
    operators.register()
    parameter_update.register()
    print("Ando Barrier Physics add-on registered")

def unregister():
    parameter_update.unregister()
    operators.unregister()
    ui.unregister()
    properties.unregister()
    print("Ando Barrier Physics add-on unregistered")

if __name__ == "__main__":
    register()
