"""
Visualization utilities for Ando Barrier Physics
Draws debug overlays for contacts, normals, and constraints
"""

import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

# Global state for visualization
_draw_handler = None
_shader = None

def get_shader():
    """Get or create shader for drawing"""
    global _shader
    if _shader is None:
        _shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    return _shader

def draw_debug_callback():
    """Draw debug visualization in 3D viewport"""
    from . import operators
    sim_state = operators._sim_state
    
    if not sim_state['initialized']:
        return
    
    shader = get_shader()
    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('LESS_EQUAL')
    gpu.state.line_width_set(2.0)
    gpu.state.point_size_set(8.0)
    
    # Draw contact points (red dots)
    if sim_state['debug_contacts']:
        positions = [contact[0] for contact in sim_state['debug_contacts']]
        batch = batch_for_shader(shader, 'POINTS', {"pos": positions})
        shader.bind()
        shader.uniform_float("color", (1.0, 0.0, 0.0, 1.0))  # Red
        batch.draw(shader)
        
        # Draw contact normals (green lines)
        lines = []
        for pos, normal in sim_state['debug_contacts']:
            start = Vector(pos)
            end = start + Vector(normal) * 0.05  # Scale normal for visibility
            lines.extend([start, end])
        
        if lines:
            batch = batch_for_shader(shader, 'LINES', {"pos": lines})
            shader.bind()
            shader.uniform_float("color", (0.0, 1.0, 0.0, 1.0))  # Green
            batch.draw(shader)
    
    # Draw pinned vertices (blue dots)
    if sim_state['debug_pins']:
        batch = batch_for_shader(shader, 'POINTS', {"pos": sim_state['debug_pins']})
        shader.bind()
        shader.uniform_float("color", (0.0, 0.3, 1.0, 1.0))  # Blue
        batch.draw(shader)
    
    # Restore default state
    gpu.state.blend_set('NONE')
    gpu.state.depth_test_set('LESS_EQUAL')
    gpu.state.line_width_set(1.0)
    gpu.state.point_size_set(1.0)

def enable_debug_visualization():
    """Enable debug visualization overlay"""
    global _draw_handler
    
    if _draw_handler is None:
        # Add draw handler to all 3D views
        _draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            draw_debug_callback,
            (),
            'WINDOW',
            'POST_VIEW'
        )
        
        # Force viewport update
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

def disable_debug_visualization():
    """Disable debug visualization overlay"""
    global _draw_handler
    
    if _draw_handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handler, 'WINDOW')
        _draw_handler = None
        
        # Force viewport update
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

def is_visualization_enabled():
    """Check if visualization is currently enabled"""
    return _draw_handler is not None

def update_debug_data(contacts=None, pins=None, stats=None):
    """Update debug visualization data"""
    from . import operators
    sim_state = operators._sim_state
    
    if contacts is not None:
        sim_state['debug_contacts'] = contacts
    if pins is not None:
        sim_state['debug_pins'] = pins
    if stats is not None:
        sim_state['stats'].update(stats)
    
    # Force viewport redraw
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()
