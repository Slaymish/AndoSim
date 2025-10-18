#!/usr/bin/env python3
"""
Simpler test based on PyVista docs pattern
"""

import os

os.environ.setdefault("PYVISTA_INTERACTIVE", "1")
os.environ.setdefault("PYVISTA_OFF_SCREEN", "0")

import pyvista as pv

pv.OFF_SCREEN = False
pv.BUILDING_GALLERY = False
pv.global_theme.interactive = True
if hasattr(pv.global_theme, "notebook"):
    pv.global_theme.notebook = False

print("PyVista Key Event Test")
print("=" * 50)
print("Try pressing 'k' or 'space'")
print("Close window with 'q'")
print()

# State
state = {'message': 'Press k or space!'}

# Create sphere
sphere = pv.Sphere()

# Plotter
p = pv.Plotter()
p.theme.interactive = True
iren = getattr(p, "iren", None)
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
p.add_mesh(sphere, color='tan')

# Define callback BEFORE show()
def callback_k():
    state['message'] = 'K was pressed!'
    print(state['message'])
    p.add_text(state['message'], position='upper_left', font_size=20, name='msg')

def callback_space():
    state['message'] = 'SPACE was pressed!'
    print(state['message'])
    p.add_text(state['message'], position='upper_left', font_size=20, name='msg')

# Add events BEFORE show()
p.add_key_event('k', callback_k)
p.add_key_event('space', callback_space)

# Add initial text
p.add_text(state['message'], position='upper_left', font_size=20, name='msg')

# Now show
p.show()

print("\nDone!")
