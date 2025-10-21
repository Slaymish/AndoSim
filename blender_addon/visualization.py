"""
Visualization utilities for Ando Barrier Physics
Draws debug overlays for contacts, normals, constraints, and heatmaps
"""

import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
import numpy as np

from ._core_loader import get_core_module

# Global state for visualization
_draw_handler = None
_shader = None
_flat_shader = None

# Heatmap data cache
_heatmap_cache = {
    'gap_colors': None,
    'gap_vertices': None,
    'gap_indices': None,
    'strain_colors': None,
    'strain_vertices': None,
    'strain_indices': None,
}

# Color palette per contact type (R, G, B, A)
CONTACT_COLORS = {
    'POINT_TRIANGLE': (1.0, 0.15, 0.15, 1.0),  # Red
    'EDGE_EDGE': (1.0, 0.6, 0.05, 1.0),        # Orange
    'WALL': (0.8, 0.8, 0.2, 1.0),              # Yellow
}
DEFAULT_CONTACT_COLOR = (0.9, 0.9, 0.9, 1.0)    # Light gray for unknown types


def get_shader():
    """Get or create shader for drawing"""
    global _shader
    if (_shader is None):
        _shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    return _shader

def get_flat_shader():
    """Get or create flat color shader for per-vertex colors"""
    global _flat_shader
    if _flat_shader is None:
        _flat_shader = gpu.shader.from_builtin('SMOOTH_COLOR')
    return _flat_shader

def gap_to_color(gap, gap_max=0.001):
    """
    Convert gap distance to heatmap color
    
    Args:
        gap: Gap distance in meters
        gap_max: Maximum gap distance for color mapping
        
    Returns:
        (r, g, b, a) tuple
    """
    # Normalize gap to [0, 1]
    t = min(gap / gap_max, 1.0)
    
    # Color mapping:
    # Red (t=0, contact) -> Yellow (t=0.3) -> Green (t=1.0, safe)
    if t < 0.3:
        # Red to Yellow
        s = t / 0.3
        r = 1.0
        g = s
        b = 0.0
    else:
        # Yellow to Green
        s = (t - 0.3) / 0.7
        r = 1.0 - s
        g = 1.0
        b = 0.0
    
    return (r, g, b, 0.7)  # Semi-transparent

def strain_to_color(strain, strain_limit=0.05):
    """
    Convert strain magnitude to heatmap color
    
    Args:
        strain: Strain value (σ_max - 1.0, where 1.0 is no stretch)
        strain_limit: Strain limit threshold
        
    Returns:
        (r, g, b, a) tuple
    """
    # Normalize strain to [0, 1] relative to limit
    t = min(strain / strain_limit, 1.0)
    
    # Color mapping:
    # Blue (t=0, no stretch) -> Green (t=0.3) -> Yellow (t=0.7) -> Red (t=1.0, at limit)
    if t < 0.3:
        # Blue to Green
        s = t / 0.3
        r = 0.0
        g = s
        b = 1.0 - s
    elif t < 0.7:
        # Green to Yellow
        s = (t - 0.3) / 0.4
        r = s
        g = 1.0
        b = 0.0
    else:
        # Yellow to Red
        s = (t - 0.7) / 0.3
        r = 1.0
        g = 1.0 - s
        b = 0.0
    
    return (r, g, b, 0.7)  # Semi-transparent

def compute_gap_heatmap(mesh_obj, contacts, gap_max=0.001):
    """
    Compute gap heatmap for mesh faces
    
    Args:
        mesh_obj: Blender mesh object
        contacts: List of contact dictionaries with 'position' and 'gap'
        gap_max: Maximum gap for color mapping
        
    Returns:
        (vertices, indices, colors) for rendering
    """
    if not contacts or not mesh_obj or not mesh_obj.data:
        return None, None, None
    
    mesh = mesh_obj.data
    matrix_world = mesh_obj.matrix_world
    
    # Build spatial lookup: for each face, find nearest contact
    face_gaps = np.full(len(mesh.polygons), gap_max * 2.0)  # Initialize with large gap
    
    for contact in contacts:
        contact_pos = Vector(contact['position'])
        contact_gap = contact.get('gap', gap_max)
        
        # Find closest face to this contact
        for i, poly in enumerate(mesh.polygons):
            # Compute face center in world space
            face_center = matrix_world @ poly.center
            distance = (face_center - contact_pos).length
            
            # If this contact is close to this face, update gap
            if distance < gap_max * 2.0:
                face_gaps[i] = min(face_gaps[i], contact_gap)
    
    # Build render geometry with per-vertex colors
    vertices = []
    indices = []
    colors = []
    vertex_offset = 0
    
    for i, poly in enumerate(mesh.polygons):
        gap = face_gaps[i]
        color = gap_to_color(gap, gap_max)
        
        # Add face vertices
        for loop_idx in poly.loop_indices:
            vert_idx = mesh.loops[loop_idx].vertex_index
            vert_pos = matrix_world @ mesh.vertices[vert_idx].co
            vertices.append(vert_pos)
            colors.append(color)
        
        # Triangulate face (simple fan triangulation)
        num_verts = len(poly.loop_indices)
        for j in range(1, num_verts - 1):
            indices.extend([vertex_offset, vertex_offset + j, vertex_offset + j + 1])
        
        vertex_offset += num_verts
    
    return vertices, indices, colors

def compute_strain_heatmap(mesh_obj, state, strain_limit=0.05):
    """
    Compute strain heatmap for mesh faces
    
    Args:
        mesh_obj: Blender mesh object
        state: Simulation state with positions
        strain_limit: Strain limit threshold
        
    Returns:
        (vertices, indices, colors) for rendering
    """
    if not mesh_obj or not mesh_obj.data:
        return None, None, None
    
    abc = get_core_module(context="Visualization strain heatmap")
    if abc is None:
        return None, None, None
    
    mesh = mesh_obj.data
    matrix_world = mesh_obj.matrix_world
    
    # Extract mesh topology
    positions = []
    for v in mesh.vertices:
        world_pos = matrix_world @ v.co
        positions.extend([world_pos.x, world_pos.y, world_pos.z])
    
    triangles = []
    for poly in mesh.polygons:
        if len(poly.vertices) >= 3:
            triangles.extend([poly.vertices[0], poly.vertices[1], poly.vertices[2]])
    
    if not triangles:
        return None, None, None
    
    # Create temporary mesh for strain computation
    from . import operators
    rest_mesh = operators._create_mesh_from_blender(mesh_obj)
    
    # Compute per-face strain (σ_max - 1.0)
    num_faces = len(triangles) // 3
    face_strains = []
    
    for face_idx in range(num_faces):
        tri_start = face_idx * 3
        v0_idx = triangles[tri_start + 0]
        v1_idx = triangles[tri_start + 1]
        v2_idx = triangles[tri_start + 2]
        
        # Get current positions
        v0 = Vector(positions[v0_idx*3:v0_idx*3+3])
        v1 = Vector(positions[v1_idx*3:v1_idx*3+3])
        v2 = Vector(positions[v2_idx*3:v2_idx*3+3])
        
        # Get rest positions
        rest_v0 = rest_mesh.get_vertex_position(v0_idx)
        rest_v1 = rest_mesh.get_vertex_position(v1_idx)
        rest_v2 = rest_mesh.get_vertex_position(v2_idx)
        
        # Compute deformation gradient (simplified 2D)
        e1_rest = Vector(rest_v1) - Vector(rest_v0)
        e2_rest = Vector(rest_v2) - Vector(rest_v0)
        e1_curr = v1 - v0
        e2_curr = v2 - v0
        
        # Compute stretch ratios (approximate σ_max)
        stretch1 = e1_curr.length / max(e1_rest.length, 1e-6)
        stretch2 = e2_curr.length / max(e2_rest.length, 1e-6)
        sigma_max = max(stretch1, stretch2)
        
        # Strain is (σ_max - 1.0)
        strain = max(sigma_max - 1.0, 0.0)
        face_strains.append(strain)
    
    # Build render geometry
    vertices = []
    indices = []
    colors = []
    vertex_offset = 0
    
    for i, poly in enumerate(mesh.polygons):
        strain = face_strains[i] if i < len(face_strains) else 0.0
        color = strain_to_color(strain, strain_limit)
        
        # Add face vertices
        for loop_idx in poly.loop_indices:
            vert_idx = mesh.loops[loop_idx].vertex_index
            vert_pos = matrix_world @ mesh.vertices[vert_idx].co
            vertices.append(vert_pos)
            colors.append(color)
        
        # Triangulate face
        num_verts = len(poly.loop_indices)
        for j in range(1, num_verts - 1):
            indices.extend([vertex_offset, vertex_offset + j, vertex_offset + j + 1])
        
        vertex_offset += num_verts
    
    return vertices, indices, colors

def draw_debug_callback():
    """Draw debug visualization in 3D viewport"""
    from . import operators
    sim_state = operators._sim_state
    
    if not sim_state['initialized']:
        return
    
    props = bpy.context.scene.ando_barrier
    
    shader = get_shader()
    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('LESS_EQUAL')
    
    # Draw gap heatmap if enabled
    if props.show_gap_heatmap and _heatmap_cache['gap_vertices']:
        try:
            flat_shader = get_flat_shader()
            batch = batch_for_shader(
                flat_shader,
                'TRIS',
                {
                    "pos": _heatmap_cache['gap_vertices'],
                    "color": _heatmap_cache['gap_colors'],
                },
                indices=_heatmap_cache['gap_indices']
            )
            flat_shader.bind()
            batch.draw(flat_shader)
        except Exception as e:
            print(f"Error drawing gap heatmap: {e}")
    
    # Draw strain heatmap if enabled
    if props.show_strain_overlay and _heatmap_cache['strain_vertices']:
        try:
            flat_shader = get_flat_shader()
            batch = batch_for_shader(
                flat_shader,
                'TRIS',
                {
                    "pos": _heatmap_cache['strain_vertices'],
                    "color": _heatmap_cache['strain_colors'],
                },
                indices=_heatmap_cache['strain_indices']
            )
            flat_shader.bind()
            batch.draw(flat_shader)
        except Exception as e:
            print(f"Error drawing strain overlay: {e}")
    
    # Draw contact visualization (if not showing heatmaps)
    if not props.show_gap_heatmap and not props.show_strain_overlay:
        gpu.state.line_width_set(2.0)
        gpu.state.point_size_set(8.0)

        # Draw contact points grouped by type
        contact_groups = {}
        for contact in sim_state['debug_contacts']:
            ctype = contact.get('type', 'UNKNOWN')
            contact_groups.setdefault(ctype, []).append(contact)

        for contact_type, contacts in contact_groups.items():
            color = CONTACT_COLORS.get(contact_type, DEFAULT_CONTACT_COLOR)

            positions = [Vector(contact['position']) for contact in contacts]
            if positions:
                batch = batch_for_shader(shader, 'POINTS', {"pos": positions})
                shader.bind()
                shader.uniform_float("color", color)
                batch.draw(shader)

            # Draw contact normals as lines with half alpha for readability
            lines = []
            for contact in contacts:
                start = Vector(contact['position'])
                end = start + Vector(contact['normal']) * 0.05  # Scale normal for visibility
                lines.extend([start, end])

            if lines:
                line_batch = batch_for_shader(shader, 'LINES', {"pos": lines})
                shader.bind()
                r, g, b, a = color
                shader.uniform_float("color", (r, g, b, min(1.0, a * 0.6)))
                line_batch.draw(shader)
    
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

def update_gap_heatmap(mesh_obj, contacts=None, gap_max=None):
    """Update gap heatmap data for rendering"""
    global _heatmap_cache
    
    if gap_max is None:
        gap_max = bpy.context.scene.ando_barrier.contact_gap_max
    
    vertices, indices, colors = compute_gap_heatmap(mesh_obj, contacts or [], gap_max)
    
    _heatmap_cache['gap_vertices'] = vertices
    _heatmap_cache['gap_indices'] = indices
    _heatmap_cache['gap_colors'] = colors
    
    # Force viewport redraw
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()

def update_strain_heatmap(mesh_obj, state=None, strain_limit=None):
    """Update strain heatmap data for rendering"""
    global _heatmap_cache
    
    if strain_limit is None:
        strain_limit = bpy.context.scene.ando_barrier.strain_limit / 100.0  # Convert from percentage
    
    vertices, indices, colors = compute_strain_heatmap(mesh_obj, state, strain_limit)
    
    _heatmap_cache['strain_vertices'] = vertices
    _heatmap_cache['strain_indices'] = indices
    _heatmap_cache['strain_colors'] = colors
    
    # Force viewport redraw
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()

def clear_heatmap_cache():
    """Clear all cached heatmap data"""
    global _heatmap_cache
    _heatmap_cache = {
        'gap_colors': None,
        'gap_vertices': None,
        'gap_indices': None,
        'strain_colors': None,
        'strain_vertices': None,
        'strain_indices': None,
    }
