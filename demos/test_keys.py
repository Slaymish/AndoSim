#!/usr/bin/env python3
"""
Minimal test to debug PyVista key events
"""

import os

os.environ.setdefault("PYVISTA_INTERACTIVE", "1")
os.environ.setdefault("PYVISTA_OFF_SCREEN", "0")

import pyvista as pv
import numpy as np

pv.OFF_SCREEN = False
pv.BUILDING_GALLERY = False
pv.global_theme.interactive = True
if hasattr(pv.global_theme, "notebook"):
    pv.global_theme.notebook = False

print("Testing PyVista key events...")
print("Try pressing: Space, a, Left, Right, q")
print()

# Create simple sphere
sphere = pv.Sphere()

# Track what gets called
state = {'count': 0}

def on_any_key():
    """Test if ANY key works"""
    state['count'] += 1
    print(f"Key pressed! Count: {state['count']}")

# Create plotter
plotter = pv.Plotter()
plotter.theme.interactive = True
iren = getattr(plotter, "iren", None)
vtk_iren = getattr(iren, "interactor", None) if iren is not None else None
try:
    if iren is not None and hasattr(iren, "initialize"):
        iren.initialize()
    if vtk_iren is not None:
        if hasattr(vtk_iren, "Initialize"):
            vtk_iren.Initialize()
        if hasattr(vtk_iren, "Enable"):
            vtk_iren.Enable()
except Exception as exc:
    print(f"Warning: interactor init failed ({exc})")
plotter.add_mesh(sphere)

# Try multiple key bindings
print("Registering key events:")
print("  Space → on_any_key")
print("  a → on_any_key")
print("  Left → on_any_key")
print("  Right → on_any_key")
print()

plotter.add_key_event('space', on_any_key)  # Try lowercase
plotter.add_key_event('a', on_any_key)
plotter.add_key_event('Left', on_any_key)
plotter.add_key_event('Right', on_any_key)

print("Window opening - try pressing keys!")
print("Close with 'q' or window close button")
print()

plotter.show()

print(f"\nTotal key presses detected: {state['count']}")
