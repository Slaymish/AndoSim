#!/usr/bin/env python3
"""
Simpler test based on PyVista docs pattern
"""

import pyvista as pv

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
