"""Render README animation frames for AndoSim.

blender -b --factory-startup --python docs/example_images/render_demo.py -- \
    --scene drape|swing --frames 60 --out DIR [--res 900 700] [--samples 48]
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

import blender_addon as addon  # noqa: E402

addon.register()


def args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument('--scene', default='drape')
    p.add_argument('--frames', type=int, default=60)
    p.add_argument('--out', required=True)
    p.add_argument('--res', type=int, nargs=2, default=[900, 700])
    p.add_argument('--samples', type=int, default=48)
    p.add_argument('--render-every', type=int, default=2)
    p.add_argument('--dt', type=float, default=1.0)
    p.add_argument('--gap', type=float, default=0.002)
    p.add_argument('--check', action='store_true')
    return p.parse_args(argv)


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


def cloth_material(obj: bpy.types.Object, base=(0.62, 0.09, 0.11)) -> None:
    mat = bpy.data.materials.new('ClothMat')
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes['Principled BSDF']
    bsdf.inputs['Roughness'].default_value = 0.55
    bsdf.inputs['Sheen Weight'].default_value = 0.6
    bsdf.inputs['Sheen Roughness'].default_value = 0.4
    uv = nt.nodes.new('ShaderNodeTexCoord')
    checker = nt.nodes.new('ShaderNodeTexChecker')
    checker.inputs['Scale'].default_value = 40.0
    checker.inputs['Color1'].default_value = (*base, 1.0)
    darker = tuple(c * 0.55 for c in base)
    checker.inputs['Color2'].default_value = (*darker, 1.0)
    nt.links.new(uv.outputs['UV'], checker.inputs['Vector'])
    nt.links.new(checker.outputs['Color'], bsdf.inputs['Base Color'])
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


def setup(scene: str, frames: int, dt: float, gap: float):
    clear()
    studio()
    area_light('Key', 420, 3.2, (2.6, -3.0, 2.6), (0, 0, 0.15))
    area_light('Fill', 90, 4.0, (-3.2, -1.8, 0.6), (0, 0, 0.1), (0.75, 0.82, 1.0))
    area_light('Rim', 220, 2.0, (-1.6, 3.2, 1.9), (0, 0, 0.3), (1.0, 0.85, 0.7))

    if scene == 'drape':
        obj = grid(29, 25, 2.0, 'XZ')
        obj.location = (0.0, 0.0, 0.0)
        cloth_material(obj, (0.60, 0.08, 0.10))
        xs = [v.co.x for v in obj.data.vertices if v.co.z > 0.99]
        corners = [v.index for v in obj.data.vertices
                   if v.co.z > 0.99 and (abs(v.co.x - min(xs)) < 1e-6 or abs(v.co.x - max(xs)) < 1e-6)]
        vg = obj.vertex_groups.new(name='ando_pins')
        vg.add(corners, 1.0, 'ADD')
        camera((2.45, -4.65, 0.78), (0.0, 0.0, 0.02), lens=42)
    elif scene == 'wave':
        # A corrugated sheet pinned at two corners: gravity pulls the folds
        # straight, which shows the elasticity without any contact to resolve.
        obj = grid(37, 25, 2.0, 'XZ')
        for v in obj.data.vertices:
            v.co.y += 0.16 * math.sin(3.0 * math.pi * (v.co.x / 2.0 + 0.5))
        obj.data.update()
        cloth_material(obj, (0.16, 0.38, 0.30))
        xs = [v.co.x for v in obj.data.vertices if v.co.z > 0.99]
        corners = [v.index for v in obj.data.vertices
                   if v.co.z > 0.99 and (abs(v.co.x - min(xs)) < 1e-6 or abs(v.co.x - max(xs)) < 1e-6)]
        vg = obj.vertex_groups.new(name='ando_pins')
        vg.add(corners, 1.0, 'ADD')
        camera((1.95, -3.15, 0.35), (0.0, 0.0, -0.02), lens=56)
    elif scene == 'swing':
        obj = grid(33, 21, 2.2, 'XZ')
        cloth_material(obj, (0.10, 0.26, 0.52))
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
    props.contact_gap_max = gap
    props.wall_gap = gap
    props.enable_ground_plane = False
    props.enable_friction = True
    props.enable_strain_limiting = False
    obj.ando_barrier_body.enabled = True
    obj.ando_barrier_body.role = 'DEFORMABLE'

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


def main() -> None:
    a = args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    obj = setup(a.scene, a.frames, a.dt, a.gap)
    sc = bpy.context.scene
    sc.cycles.samples = a.samples
    sc.render.resolution_x, sc.render.resolution_y = a.res

    t0 = time.time()
    result = bpy.ops.ando.bake_simulation()
    print(f'[render] bake={result} {time.time() - t0:.1f}s', flush=True)

    keys = [k for k in obj.data.shape_keys.key_blocks if k.name.startswith('frame_')]
    zs = [float(np.mean([v.co[2] for v in k.data])) for k in keys]
    lows = [float(min(v.co[2] for v in k.data)) for k in keys]
    print(f'[render] keys={len(keys)} z_first={zs[0]:.4f} z_last={zs[-1]:.4f} '
          f'min={min(lows):.4f} max={max(zs):.4f}', flush=True)
    if a.check:
        return

    for i, frame in enumerate(range(1, a.frames + 1, a.render_every)):
        sc.frame_set(frame)
        sc.render.filepath = str(out / f'f{i:03d}.png')
        bpy.ops.render.render(write_still=True)
        print(f'[render] {i} frame {frame}', flush=True)


main()
