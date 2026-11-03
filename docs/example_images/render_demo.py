"""Render README animation frames for AndoSim.

blender -b --factory-startup --python docs/example_images/render_demo.py -- \
    --scene sphere|showcase|drape|wave|swing --frames 12 --out DIR [--res 900 700] [--samples 48]
"""
from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

# Preload before importing the addon: CPython caches extension initialization by
# module name, so replacing an already imported binary can silently reuse it.
if '--core' in sys.argv:
    import importlib.util
    core_path = Path(sys.argv[sys.argv.index('--core') + 1]).resolve()
    core_name = 'blender_addon.ando_barrier_core'
    spec = importlib.util.spec_from_file_location(core_name, core_path)
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    sys.modules[core_name] = native

import blender_addon as addon  # noqa: E402

addon.register()


def args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument('--scene', choices=['sphere', 'showcase', 'drape', 'wave', 'swing'], default='showcase')
    p.add_argument('--frames', type=int, default=12)
    p.add_argument('--out', required=True)
    p.add_argument('--res', type=int, nargs=2, default=[900, 700])
    p.add_argument('--samples', type=int, default=48)
    p.add_argument('--render-every', type=int, default=2)
    p.add_argument('--dt', type=float, default=0.5, help='Solver timestep cap in milliseconds')
    p.add_argument('--gap', type=float, default=0.002)
    p.add_argument('--check', action='store_true')
    p.add_argument('--core', type=Path, help='Explicit native extension to validate')
    p.add_argument('--margin', type=float, default=1.18)
    p.add_argument('--cam-dir', type=float, nargs=3, default=[0.52, -1.0, 0.10])
    a = p.parse_args(argv)
    if a.frames < 2 or a.render_every < 1 or min(a.res) < 16 or a.samples < 1:
        p.error('frames >= 2, render-every >= 1, res >= 16 and samples >= 1 required')
    if not math.isfinite(a.gap) or a.gap <= 0:
        p.error('gap must be finite and positive')
    if not (0.1 <= a.dt <= 10) or not math.isfinite(a.margin) or a.margin < 1:
        p.error('dt must be 0.1..10 ms and margin finite and >= 1')
    if not all(math.isfinite(x) for x in a.cam_dir) or sum(x*x for x in a.cam_dir) < 1e-12:
        p.error('cam-dir must be finite and nonzero')
    return a


def clear() -> None:
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()


def grid(nx: int, ny: int, size: float, plane: str) -> bpy.types.Object:
    verts, faces = [], []
    for j in range(ny):
        for i in range(nx):
            u = (i / (nx - 1) - 0.5) * size
            v = (j / (ny - 1) - 0.5) * size
            verts.append((u, 0.0, v) if plane == 'XZ' else (u, v, 0.0))
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            faces.append((a, a + 1, a + nx + 1, a + nx))
    mesh = bpy.data.meshes.new('ClothMesh')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    # Planar UVs so the checker texture actually has coordinates to read.
    uv_layer = mesh.uv_layers.new(name='UVMap')
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            vidx = mesh.loops[li].vertex_index
            i, j = vidx % nx, vidx // nx
            uv_layer.data[li].uv = (i / (nx - 1), j / (ny - 1))
    obj = bpy.data.objects.new('Cloth', mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def cloth_material(obj: bpy.types.Object, base=(0.55, 0.07, 0.09)) -> None:
    """Solid fabric with a fine weave in the bump, so it reads as cloth."""
    mat = bpy.data.materials.new('ClothMat')
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (*base, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.62
    bsdf.inputs['Sheen Weight'].default_value = 0.7
    bsdf.inputs['Sheen Roughness'].default_value = 0.35
    bsdf.inputs['Specular IOR Level'].default_value = 0.35

    weave = nt.nodes.new('ShaderNodeTexWave')
    weave.wave_type = 'BANDS'
    weave.bands_direction = 'DIAGONAL'
    weave.inputs['Scale'].default_value = 220.0
    weave.inputs['Distortion'].default_value = 1.5

    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.14
    bump.inputs['Distance'].default_value = 0.002
    nt.links.new(weave.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    obj.data.materials.append(mat)


def studio(size=14.0, z=-1.15) -> None:
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, z))
    floor = bpy.context.active_object
    floor.name = 'Cyclorama'
    mat = bpy.data.materials.new('StudioMat')
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (0.055, 0.06, 0.07, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.42
    floor.data.materials.append(mat)
    floor.select_set(False)

    world = bpy.context.scene.world or bpy.data.worlds.new('World')
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.012, 0.014, 0.018, 1.0)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6


def aim(obj, target) -> None:
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()


def area_light(name, energy, size, location, target, color=(1.0, 0.97, 0.93)):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = energy
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    aim(obj, target)
    return obj


def camera(location, target, lens=52) -> None:
    data = bpy.data.cameras.new('Cam')
    data.lens = lens
    cam = bpy.data.objects.new('Cam', data)
    bpy.context.collection.objects.link(cam)
    cam.location = location
    aim(cam, target)
    bpy.context.scene.camera = cam



def frame_cloth(obj, direction=(0.52, -1.0, 0.10), lens=45, margin=1.18) -> None:
    """Place the camera so the whole deformation stays in frame, however far it sags."""
    import mathutils

    keys = [k for k in obj.data.shape_keys.key_blocks if k.name == 'Basis' or k.name.startswith('frame_')]
    pts = []
    for k in keys:
        for vert in k.data:
            pts.append(obj.matrix_world @ vert.co)
    if not pts:
        return
    if 'Native rigid sphere' in bpy.data.objects:
        sphere = bpy.data.objects['Native rigid sphere']
        pts.extend(sphere.matrix_world @ v.co for v in sphere.data.vertices)
    lo = mathutils.Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = mathutils.Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    centre = (lo + hi) / 2.0
    radius = (hi - lo).length / 2.0

    cam_data = bpy.data.cameras.new('AutoCam')
    cam_data.lens = lens
    sc = bpy.context.scene
    aspect = (sc.render.resolution_x * sc.render.pixel_aspect_x /
              (sc.render.resolution_y * sc.render.pixel_aspect_y))
    cam_data.sensor_fit = 'HORIZONTAL'
    d = mathutils.Vector(direction).normalized()
    rotation = (-d).to_track_quat('-Z', 'Y')
    right = rotation @ Vector((1, 0, 0))
    up = rotation @ Vector((0, 1, 0))
    tan_x, tan_y = 18.0 / lens, 18.0 / lens / aspect
    distance = max((p-centre).dot(d) + margin * max(
        abs((p-centre).dot(right)) / tan_x,
        abs((p-centre).dot(up)) / tan_y) for p in pts)
    cam = bpy.data.objects.new('AutoCam', cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = centre + d * distance
    aim(cam, centre)
    bpy.context.scene.camera = cam
    print(f'[render] framed centre={tuple(round(c, 2) for c in centre)} radius={radius:.2f} '
          f'distance={distance:.2f}', flush=True)

def setup(scene: str, frames: int, dt: float, gap: float):
    clear()
    studio()
    area_light('Key', 420, 3.2, (2.6, -3.0, 2.6), (0, 0, 0.15))
    area_light('Fill', 90, 4.0, (-3.2, -1.8, 0.6), (0, 0, 0.1), (0.75, 0.82, 1.0))
    area_light('Rim', 220, 2.0, (-1.6, 3.2, 1.9), (0, 0, 0.3), (1.0, 0.85, 0.7))

    if scene == 'sphere':
        # Initial rest geometry only. All subsequent motion is a native bake.
        obj = grid(17, 17, 2.8, 'XY')
        for v in obj.data.vertices:
            v.co.z = 1.08 + .10 * v.co.x + .035 * math.sin(5 * v.co.y)
        obj.data.update()
        cloth_material(obj, (.015, .19, .22))
        cloth_material(obj, (.65, .16, .025))
        for poly in obj.data.polygons:
            poly.material_index = int(poly.index % 16 in (0, 1, 12, 15))
            poly.use_smooth = True
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=.72)
        sphere = bpy.context.object
        sphere.name = 'Native rigid sphere'
        sphere.ando_barrier_body.enabled = True
        sphere.ando_barrier_body.role = 'RIGID'
        sphere.ando_barrier_body.rigid_density = 20000
        mat = bpy.data.materials.new('Copper collider')
        mat.use_nodes = True
        bs = mat.node_tree.nodes['Principled BSDF']
        bs.inputs['Base Color'].default_value = (.32, .065, .018, 1)
        bs.inputs['Metallic'].default_value = .78
        bs.inputs['Roughness'].default_value = .24
        sphere.data.materials.append(mat)
        # Keep the rendered surface identical to collision geometry.
        bpy.data.objects['Cyclorama'].location.z = -2.5
        area_light('Canopy softbox', 350, 3, (0, -2, 4), (0, 0, .5))
    elif scene == 'showcase':
        # Rest geometry only: a broad elastic sail released 55 degrees from vertical.
        # The straight upper edge is fixed; every other vertex is solver-driven.
        obj = grid(29, 25, 2.4, 'XZ')
        for v in obj.data.vertices:
            u = v.co.x / 2.4 + 0.5
            t = (1.2 - v.co.z) / 2.4
            v.co.x *= 1.0 - 0.22 * t
            v.co.y = -2.4 * t * math.sin(math.radians(55))
            v.co.z = 1.2 - 2.4 * t * math.cos(math.radians(55))
            v.co.y += 0.32 * math.sin(3 * math.pi * u + 0.4) * math.sin(math.pi * t / 2)
            v.co.z += 0.16 * math.sin(math.pi * u) * t
        obj.data.update()
        cloth_material(obj, (0.012, 0.15, 0.13))
        # Woven copper selvedges and a wide asymmetric accent, in material only.
        cloth_material(obj, (0.42, 0.12, 0.025))
        for poly in obj.data.polygons:
            col = poly.index % 28
            poly.material_index = int(col in (0, 1, 20, 21, 27))
            poly.use_smooth = True
        vg = obj.vertex_groups.new(name='ando_pins')
        vg.add(list(range(24 * 29, 25 * 29)), 1.0, 'ADD')
        # Display hardware is decorative, never registered as a collider.
        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.025, depth=2.65,
                                           location=(0, 0, 1.23),
                                           rotation=(0, math.pi / 2, 0))
        rail = bpy.context.object
        rail.name = 'Fixed suspension rail (display only)'
        mat = bpy.data.materials.new('Brushed brass')
        mat.diffuse_color = (0.42, 0.23, 0.07, 1)
        mat.use_nodes = True
        bs = mat.node_tree.nodes['Principled BSDF']
        bs.inputs['Base Color'].default_value = (0.42, 0.23, 0.07, 1)
        bs.inputs['Metallic'].default_value = 0.8
        bs.inputs['Roughness'].default_value = 0.28
        rail.data.materials.append(mat)
        bpy.data.objects['Cyclorama'].location.z = -2.6
        area_light('Silk softbox', 240, 3.0, (0, -4, 4), (0, -0.6, 0))
    elif scene == 'drape':
        obj = grid(23, 19, 2.0, 'XZ')
        obj.location = (0.0, 0.0, 0.0)
        cloth_material(obj, (0.52, 0.06, 0.08))
        xs = [v.co.x for v in obj.data.vertices if v.co.z > 0.99]
        corners = [v.index for v in obj.data.vertices
                   if v.co.z > 0.99 and (abs(v.co.x - min(xs)) < 1e-6 or abs(v.co.x - max(xs)) < 1e-6)]
        vg = obj.vertex_groups.new(name='ando_pins')
        vg.add(corners, 1.0, 'ADD')
        camera((2.55, -4.35, 0.30), (0.0, 0.0, -0.38), lens=42)
    elif scene == 'wave':
        # A corrugated sheet pinned at two corners: gravity pulls the folds
        # straight, which shows the elasticity without any contact to resolve.
        obj = grid(37, 25, 2.0, 'XZ')
        for v in obj.data.vertices:
            v.co.y += 0.16 * math.sin(3.0 * math.pi * (v.co.x / 2.0 + 0.5))
        obj.data.update()
        cloth_material(obj, (0.10, 0.26, 0.20))
        xs = [v.co.x for v in obj.data.vertices if v.co.z > 0.99]
        corners = [v.index for v in obj.data.vertices
                   if v.co.z > 0.99 and (abs(v.co.x - min(xs)) < 1e-6 or abs(v.co.x - max(xs)) < 1e-6)]
        vg = obj.vertex_groups.new(name='ando_pins')
        vg.add(corners, 1.0, 'ADD')
        camera((1.95, -3.15, 0.35), (0.0, 0.0, -0.02), lens=56)
    elif scene == 'swing':
        obj = grid(33, 21, 2.2, 'XZ')
        cloth_material(obj, (0.07, 0.16, 0.38))
        top = [v.index for v in obj.data.vertices if v.co.z > 1.09]
        vg = obj.vertex_groups.new(name='ando_pins')
        vg.add(top, 1.0, 'ADD')
        # Release it off-axis so it swings as a curtain rather than hanging dead flat.
        obj.rotation_euler = (0.0, math.radians(26.0), 0.0)
        camera((2.35, -3.5, 0.35), (0.0, 0.0, 0.05), lens=54)
    else:
        raise SystemExit(f'unknown scene {scene}')

    sc = bpy.context.scene
    props = sc.ando_barrier
    props.cache_start, props.cache_end = 1, frames
    props.dt = dt
    if scene in ('showcase', 'sphere'):
        props.material_properties.youngs_modulus = 1200.0
        props.material_properties.thickness = 0.001
        props.velocity_damping = 0.005
    if scene == 'sphere':
        props.material_properties.youngs_modulus = 2000.0
        props.velocity_damping = .2
        props.contact_restitution = 0.0
    props.contact_gap_max = gap
    props.wall_gap = gap
    props.enable_ground_plane = False
    props.enable_friction = False
    props.enable_strain_limiting = False
    obj.ando_barrier_body.enabled = True
    obj.ando_barrier_body.role = 'DEFORMABLE'

    sc.frame_start, sc.frame_end = 1, frames
    sc.render.fps = 24
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.use_denoising = True
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Punchy'

    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    return obj


def certify_showcase(coords, obj):
    """Conservative graph certificate, not a collision-solver claim.

    A triangulated disk with consistently oriented XZ triangles and a simple
    boundary is injective in that projection, hence cannot self-intersect in 3D.
    Reject folds in projection even when the 3D surface might still be safe.
    """
    obj.data.calc_loop_triangles()
    triangles = np.array([tuple(t.vertices) for t in obj.data.loop_triangles])
    nx, ny = 29, 25
    boundary = (list(range(nx)) + [j * nx + nx - 1 for j in range(1, ny)] +
                list(range(nx * ny - 2, nx * (ny - 1) - 1, -1)) +
                [j * nx for j in range(ny - 2, 0, -1)])

    def cross(a, b):
        return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]

    for frame, xyz in enumerate(coords, 1):
        projected = xyz[:, [0, 2]]
        t = projected[triangles]
        areas = cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
        if not (np.all(areas > 1e-9) or np.all(areas < -1e-9)):
            raise RuntimeError(f'Frame {frame}: cannot certify nonintersection in XZ projection')
        b = projected[boundary]
        for i in range(len(b)):
            a, end = b[i], b[(i + 1) % len(b)]
            for j in range(i + 2, len(b)):
                if i == 0 and j == len(b) - 1:
                    continue
                c, d = b[j], b[(j + 1) % len(b)]
                ab, cd = end - a, d - c
                # Strict separation also rejects touching nonadjacent edges.
                if (cross(ab, c-a) * cross(ab, d-a) <= 0 and
                        cross(cd, a-c) * cross(cd, end-c) <= 0 and
                        np.all(np.maximum(np.minimum(a, end), np.minimum(c, d)) <=
                               np.minimum(np.maximum(a, end), np.maximum(c, d)))):
                    raise RuntimeError(f'Frame {frame}: projected boundary intersects')
    floor_z = bpy.data.objects['Cyclorama'].location.z
    if coords[:, :, 2].min() <= floor_z + 0.05:
        raise RuntimeError('Cloth approaches decorative floor; contact is unsupported here')
    print(f'[render] nonintersection=PASS (XZ graph certificate, baked frames only) '
          f'floor_clearance={coords[:, :, 2].min() - floor_z:.6f}m', flush=True)


def mesh_surface_clearance(xyz, triangles, rigid_xyz, rigid_triangles):
    """Exact feature distance for disjoint triangle meshes, with signed checks.

    A closest pair lies on a vertex/face or edge/edge. BVH overlap rejects
    surface crossings; outward normals reject cloth vertices inside the sphere.
    """
    from mathutils.bvhtree import BVHTree
    xyz = np.asarray(xyz, dtype=np.float64)
    rigid_xyz = np.asarray(rigid_xyz, dtype=np.float64)
    cloth_tree = BVHTree.FromPolygons([Vector(p) for p in xyz], triangles, all_triangles=True)
    rigid_tree = BVHTree.FromPolygons([Vector(p) for p in rigid_xyz], rigid_triangles, all_triangles=True)
    if cloth_tree.overlap(rigid_tree):
        return -1.0
    minimum = float('inf')
    for p in xyz:
        point = Vector(p)
        closest, normal, _, distance = rigid_tree.find_nearest(point)
        if (point-closest).dot(normal) < -1e-7:
            return -float(distance)
        minimum = min(minimum, distance)
    for p in rigid_xyz:
        minimum = min(minimum, cloth_tree.find_nearest(Vector(p))[3])

    def edges(tris):
        return np.array(sorted({tuple(sorted((t[i], t[(i+1)%3]))) for t in tris for i in range(3)}))
    ce, re = edges(triangles), edges(rigid_triangles)
    p, q = xyz[ce[:, 0]][:, None, :], rigid_xyz[re[:, 0]][None, :, :]
    u = (xyz[ce[:, 1]]-xyz[ce[:, 0]])[:, None, :]
    v = (rigid_xyz[re[:, 1]]-rigid_xyz[re[:, 0]])[None, :, :]
    r = p-q
    dot = lambda a,b: np.sum(a*b, axis=-1)
    a, b, c, d, e = dot(u,u), dot(u,v), dot(v,v), dot(u,r), dot(v,r)
    denom = a*c-b*b
    s = np.clip(np.divide(b*e-c*d, denom, out=np.zeros_like(denom), where=denom>1e-20), 0, 1)
    t = (b*s+e)/c
    s = np.where(t<0, np.clip(-d/a,0,1), np.where(t>1, np.clip((b-d)/a,0,1),s))
    t = np.clip(t,0,1)
    distance = np.linalg.norm(r+s[...,None]*u-t[...,None]*v, axis=-1).min()
    return min(minimum, float(distance))


def main() -> None:
    a = args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.core:
        from blender_addon._core_loader import get_core_module
        module = get_core_module(context='explicit core validation')
        if Path(module.__file__).resolve() != a.core.resolve():
            raise RuntimeError('Requested native binary was not loaded')
        print(f'[render] native_core={module.__file__}', flush=True)
    obj = setup(a.scene, a.frames, a.dt, a.gap)
    sc = bpy.context.scene
    sc.cycles.samples = a.samples
    sc.render.resolution_x, sc.render.resolution_y = a.res

    # Observe native states without modifying them or any baked coordinates.
    probe = None
    if a.scene == 'sphere':
        from blender_addon._core_loader import get_core_module
        from mathutils.geometry import closest_point_on_tri
        core = get_core_module(context='sphere validation')
        native_step = core.Integrator.step
        obj.data.calc_loop_triangles()
        tris = [tuple(t.vertices) for t in obj.data.loop_triangles]
        sphere_obj = bpy.data.objects['Native rigid sphere']
        sphere_obj.data.calc_loop_triangles()
        rigid_tris = [tuple(t.vertices) for t in sphere_obj.data.loop_triangles]
        probe = dict(steps=0, vertex_clearance=float('inf'), surface_clearance=float('inf'),
                     body_drift=0., contacts=0)
        def observed_step(mesh, state, constraints, params, bodies=None):
            native_step(mesh, state, constraints, params, bodies)
            if not bodies or len(bodies) != 1:
                raise RuntimeError('Expected one actual native rigid collider')
            center = np.asarray(bodies[0].position)
            xyz = np.asarray(state.get_positions())
            probe['steps'] += 1
            probe['body_drift'] = max(probe['body_drift'], float(np.linalg.norm(center)))
            probe['vertex_clearance'] = min(probe['vertex_clearance'],
                float(np.linalg.norm(xyz-center, axis=1).min() - .72))
            rigid_xyz = np.asarray(bodies[0].world_vertices())
            if probe['steps'] == 1:
                probe['rigid_initial'] = rigid_xyz.copy()
            probe['rigid_surface_motion'] = max(probe.get('rigid_surface_motion', 0.),
                float(np.linalg.norm(rigid_xyz-probe['rigid_initial'], axis=1).max()))
            center_vec = Vector(center)
            vectors = [Vector(p) for p in xyz]
            surface_gap = min((closest_point_on_tri(center_vec,
                *(vectors[i] for i in tri)) - center_vec).length - .72 for tri in tris)
            probe['surface_clearance'] = min(probe['surface_clearance'], surface_gap)
            actual_gap = mesh_surface_clearance(xyz, tris, rigid_xyz, rigid_tris)
            probe['mesh_clearance'] = min(probe.get('mesh_clearance', float('inf')), actual_gap)
            if actual_gap <= 0:
                raise RuntimeError(f'Native surface intersection at step {probe["steps"]}: {actual_gap}')
            if probe['steps'] % 20 == 0:
                count = sum(c.type == core.ContactType.RIGID_POINT_TRIANGLE
                            for c in core.Integrator.compute_contacts(mesh, state, bodies))
                probe['contacts'] = max(probe['contacts'], count)
        core.Integrator.step = staticmethod(observed_step)
    t0 = time.time()
    try:
        result = bpy.ops.ando.bake_simulation()
    finally:
        if probe is not None:
            core.Integrator.step = native_step
            print(f'[render] native_probe={ {k:v for k,v in probe.items() if k != "rigid_initial"} }', flush=True)
    print(f'[render] bake={result} {time.time() - t0:.1f}s', flush=True)

    if result != {'FINISHED'} or obj.data.shape_keys is None:
        raise RuntimeError('Bake failed or produced no shape keys')
    keys = [k for k in obj.data.shape_keys.key_blocks if k.name.startswith('frame_')]
    if [k.name for k in keys] != [f'frame_{f:04d}' for f in range(1, a.frames + 1)]:
        raise RuntimeError('Bake did not produce the complete requested frame range')
    coords = np.array([[tuple(v.co) for v in k.data] for k in keys])
    basis = np.array([tuple(v.co) for v in obj.data.shape_keys.key_blocks['Basis'].data])
    if not np.isfinite(coords).all() or not np.isfinite(basis).all():
        raise RuntimeError('Nonfinite baked coordinates')
    displacement = np.linalg.norm(coords - basis, axis=2)
    temporal = np.linalg.norm(coords - coords[0], axis=2)
    peak = float(temporal.max())
    if peak < 0.01:
        raise RuntimeError(f'No meaningful motion: peak temporal displacement={peak:.6g} m')
    if a.scene == 'sphere':
        # Report the conservative analytic envelope separately. The actual
        # faceted-mesh feature distance above is the acceptance criterion.
        clearance = min((closest_point_on_tri(Vector((0,0,0)),
            *(Vector(xyz[i]) for i in tri)).length - .72)
            for xyz in coords for tri in tris) - probe['body_drift']
        print(f'[render] sphere_surface_clearance_lower_bound={clearance:.9f}m', flush=True)
        if probe['mesh_clearance'] <= 0 or probe['contacts'] == 0:
            raise RuntimeError('Sphere contact validation failed')
        if probe['rigid_surface_motion'] > 1e-4 or probe['mesh_clearance'] <= probe['rigid_surface_motion']:
            raise RuntimeError('Rigid drift exceeds static render tolerance')
        print(f'[render] actual_mesh_clearance={probe["mesh_clearance"]:.9f}m (all native steps)', flush=True)
        # Save measured coordinates for independent inspection; no animation edits.
        np.savez(out / 'collision_metrics.npz', coords=coords, basis=basis,
                 clearance=clearance, **probe)
    if a.scene == 'showcase':
        certify_showcase(coords, obj)
    frame_cloth(obj, direction=tuple(a.cam_dir), lens=45, margin=a.margin)
    bpy.context.view_layer.update()
    # Check every baked vertex against the actual perspective camera and aspect.
    from bpy_extras.object_utils import world_to_camera_view
    for frame_coords in coords:
        for co in frame_coords:
            p = world_to_camera_view(sc, sc.camera, obj.matrix_world @ Vector(co))
            if p.z <= 0 or not (0.02 <= p.x <= 0.98 and 0.02 <= p.y <= 0.98):
                raise RuntimeError('Camera clips bake; increase --margin or change --cam-dir')
    print(f'[render] PASS keys={len(keys)} finite=True range={sc.frame_start}:{sc.frame_end} '
          f'peak_from_basis={displacement.max():.6f}m temporal_peak={peak:.6f}m '
          f'rms_last={np.sqrt(np.mean(temporal[-1]**2)):.6f}m camera=PASS', flush=True)
    if a.check:
        return

    render_frames = sorted(set(range(1, a.frames + 1, a.render_every)) | {a.frames})
    for i, frame in enumerate(render_frames):
        sc.frame_set(frame)
        sc.render.filepath = str(out / f'f{i:03d}.png')
        bpy.ops.render.render(write_still=True)
        print(f'[render] {i} frame {frame}', flush=True)
    if a.scene == 'sphere':
        bpy.ops.wm.save_as_mainfile(filepath=str((out / 'sphere-contact.blend').resolve()))


main()
