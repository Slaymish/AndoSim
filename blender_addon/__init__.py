bl_info = {
    "name": "Ando Barrier Physics",
    "author": "BlenderSim Project",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Ando Physics",
    "description": "Cubic Barrier with Elasticity-Inclusive Dynamic Stiffness (Ando 2024)",
    "category": "Physics",
}

import bpy
import sys
import os

# Add the compiled module path
addon_dir = os.path.dirname(__file__)
if addon_dir not in sys.path:
    sys.path.insert(0, addon_dir)

try:
    import ando_barrier_core as abc
    CORE_AVAILABLE = True
    print(f"Loaded {abc.version()}")
except ImportError as e:
    CORE_AVAILABLE = False
    print(f"Warning: ando_barrier_core not available: {e}")

from . import ui
from . import operators
from . import properties

def register():
    properties.register()
    ui.register()
    operators.register()
    print("Ando Barrier Physics add-on registered")

def unregister():
    operators.unregister()
    ui.unregister()
    properties.unregister()
    print("Ando Barrier Physics add-on unregistered")

if __name__ == "__main__":
    register()
