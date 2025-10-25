from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

import bpy
import numpy as np
from mathutils import Vector

# Make ppf frontend importable from the submodule
_PPFDIR = Path(__file__).resolve().parent.parent / "extern" / "ppf-contact-solver" / "frontend"
_PPFROOT = _PPFDIR.parent
_PPF_SOLVER_NAME = "ppf-contact-solver.exe" if sys.platform.startswith("win") else "ppf-contact-solver"
_PPF_SOLVER_PATH = _PPFROOT / "target" / "release" / _PPF_SOLVER_NAME

if _PPFDIR.exists() and str(_PPFDIR) not in sys.path:
    sys.path.append(str(_PPFDIR))

SessionManager = None
FixedScene = None
app_param = None
_PPF_IMPORT_ERROR: Optional[str] = None

if _PPFDIR.exists():
    try:
        from _session_ import SessionManager as _SessionManager  # type: ignore
        from _scene_ import FixedScene as _FixedScene  # type: ignore
        from _param_ import app_param as _app_param  # type: ignore
    except Exception as exc:  # pragma: no cover - import diagnostics
        _PPF_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"
    else:
        SessionManager = _SessionManager
        FixedScene = _FixedScene
        app_param = _app_param
else:
    _PPF_IMPORT_ERROR = f"PPF frontend not found at {_PPFDIR}"


def _cuda_available() -> bool:
    """Return True when an NVIDIA GPU is detected via nvidia-smi."""

    try:
        result = subprocess.run(["nvidia-smi"], capture_output=True, check=False)
        return result.returncode == 0
    except FileNotFoundError:
        return False
    except Exception:
        return False


def _ppf_status() -> Tuple[bool, str]:
    """Check whether the PPF frontend appears usable."""

    if not _PPFDIR.exists():
        return False, f"PPF frontend not found at {_PPFDIR}"

    if not _PPFROOT.exists():
        return False, f"PPF project root not found at {_PPFROOT}"

    if any(item is None for item in (SessionManager, FixedScene, app_param)):
        message = (
            _PPF_IMPORT_ERROR
            if _PPF_IMPORT_ERROR
            else "PPF frontend import failed (see console for details)"
        )
        return False, message

    if not _cuda_available():
        return False, "nvidia-smi not found or no NVIDIA GPU detected"

    if not _PPF_SOLVER_PATH.exists():
        return False, (
            f"PPF solver binary missing at {_PPF_SOLVER_PATH}. "
            "Build the submodule with `cargo build --release` inside extern/ppf-contact-solver."
        )

    return True, "PPF solver ready"

def is_ppf_available(reporter=None, context=None) -> bool:
    """Return ``True`` when the PPF backend can be used."""

    ok, message = _ppf_status()
    if not ok and reporter:
        try:
            reporter({'WARNING'}, message)
        except Exception:  # pragma: no cover - Blender report API guards
            pass
    return ok


def ppf_status_message() -> str:
    """Return a short status string describing the PPF backend."""

    return _ppf_status()[1]


def ppf_status() -> Tuple[bool, str]:
    """Return availability flag and status message for the PPF backend."""

    return _ppf_status()

def _mesh_to_numpy(obj, depsgraph):
    obj_eval = obj.evaluated_get(depsgraph)
    mesh = obj_eval.to_mesh()
    if mesh is None:
        return None, None
    mesh.calc_loop_triangles()
    if not mesh.loop_triangles:
        obj_eval.to_mesh_clear()
        return None, None
    M = obj_eval.matrix_world
    verts = np.array([M @ v.co for v in mesh.vertices], dtype=np.float32)
    tris = np.array([tuple(loop.vertex_index for loop in tri.loops)
                     for tri in mesh.loop_triangles], dtype=np.int32)
    obj_eval.to_mesh_clear()
    return verts, tris

def _build_fixed_scene(context) -> FixedScene:
    """Collect cloth and rigid meshes from the scene and create a FixedScene."""

    if FixedScene is None:
        raise RuntimeError(ppf_status_message())

    deps = context.evaluated_depsgraph_get()
    scene = FixedScene()
    cloth_count = 0
    rigid_count = 0

    for obj in context.scene.objects:
        if obj.type != 'MESH':
            continue
        props = getattr(obj, "ando_barrier_body", None)
        if not props or not props.enabled:
            continue

        verts, tris = _mesh_to_numpy(obj, deps)
        if verts is None or tris is None:
            continue

        # ppf uses metres. Assume your units are metres already.
        if props.role == 'DEFORMABLE':
            # Cloth id is implicit by insertion order
            scene.add.shell(obj.name, verts, tris)
            cloth_count += 1
        elif props.role == 'RIGID':
            scene.add.rigid(obj.name, verts, tris)
            rigid_count += 1

    if cloth_count == 0:
        raise ValueError("No cloth shells found for PPF scene.")
    return scene

def _map_params_from_properties(context):
    """Map your properties.py scene/material to ppf app params."""
    # Start from ppf defaults and overwrite keys you know

    if app_param is None:
        raise RuntimeError(ppf_status_message())

    p = app_param()  # returns a dict-like
    sp = context.scene.ando_barrier

    # Scene scale and timing
    p["frames"] = max(1, int(context.scene.frame_end - context.scene.frame_start + 1))
    p["dt"] = float(sp.dt)  # if you expose dt
    # Contact and friction (names in your presets; map to ppf keys where possible)
    p["enable-friction"] = bool(sp.enable_friction)
    p["mu"] = float(sp.friction_mu)
    p["restitution"] = float(sp.contact_restitution)
    p["contact-gap-max"] = float(sp.contact_gap_max)
    p["ccd"] = True  # safe default

    # Damping and strain limiting
    p["velocity-damping"] = float(sp.velocity_damping)
    p["enable-strain-limiting"] = bool(sp.enable_strain_limiting)
    p["strain-limit"] = float(sp.strain_limit)
    p["strain-tau"] = float(sp.strain_tau)

    # Solver settings can be left default at first
    return p

class PPFSession:
    """Run ppf solver, then stream verts back into Blender each modal tick."""

    @staticmethod
    def start_modal(op, context):
        ok, message = _ppf_status()
        if not ok:
            op.report({'ERROR'}, message)
            return {'CANCELLED'}
        if SessionManager is None:
            op.report({'ERROR'}, "PPF frontend unavailable")
            return {'CANCELLED'}

        try:
            scene = _build_fixed_scene(context)
        except Exception as e:
            op.report({'ERROR'}, f"PPF scene build failed: {e}")
            return {'CANCELLED'}

        params = _map_params_from_properties(context)

        # Session root lives in a temp dir under the add-on
        app_root = str((Path(bpy.app.tempdir) / "ppf_runs").resolve())
        Path(app_root).mkdir(parents=True, exist_ok=True)

        mgr = SessionManager(app_name="ando_ppf",
                             app_root=app_root,
                             proj_root=str(_PPFROOT),
                             data_dirpath=app_root)

        session = mgr.create(scene, name="")
        fixed = session.build()  # exports scene and command.sh into session dir

        # Export params to the session path
        # The frontend writes param.toml in build(), but we also update runtime params:
        for k, v in params.items():
            session.param.set(k, v)
        # Start the solver out of process
        fixed.start(force=True, blocking=False)

        # Stash paths on the operator for modal loop
        op._ppf = {
            "mgr": mgr,
            "session": session,
            "fixed": fixed,
            "outdir": Path(fixed.info.path) / "output",
            "last_frame": -1,
            "target_obj": PPFSession._pick_first_cloth_obj(context)
        }
        context.window_manager.modal_handler_add(op)
        return {'RUNNING_MODAL'}

    @staticmethod
    def _pick_first_cloth_obj(context):
        for obj in context.scene.objects:
            if obj.type == 'MESH':
                props = getattr(obj, "ando_barrier_body", None)
                if props and props.enabled and props.role == 'DEFORMABLE':
                    return obj
        return None

    @staticmethod
    def modal_tick(op, context, event):
        info = getattr(op, "_ppf", None)
        if info is None:
            return {'CANCELLED'}

        outdir = info["outdir"]
        if not outdir.exists():
            return {'PASS_THROUGH'}

        # Find latest vert_*.bin
        files = sorted(outdir.glob("vert_*.bin"))
        if not files:
            return {'PASS_THROUGH'}

        latest = files[-1]
        frame = int(latest.stem.split("_")[1])
        if frame == info["last_frame"]:
            return {'PASS_THROUGH'}

        # Load verts and write into Blender mesh
        verts = np.fromfile(latest, dtype=np.float32).reshape(-1, 3)
        target = info["target_obj"]
        if target is None or target.type != 'MESH':
            op.report({'WARNING'}, "No target cloth object to update")
            return {'PASS_THROUGH'}

        mesh = target.data
        if mesh and len(mesh.vertices) == len(verts):
            if target.mode != 'OBJECT':
                op.report({'WARNING'}, "Switch object out of Edit Mode to update geometry")
                return {'PASS_THROUGH'}

            to_local = target.matrix_world.inverted_safe()
            local_coords = [to_local @ Vector(coord) for coord in verts]
            for idx, vertex in enumerate(mesh.vertices):
                vertex.co = local_coords[idx]
            mesh.update()
            info["last_frame"] = frame
            context.view_layer.update()

        # Termination check
        finished_flag = (Path(info["fixed"].output.path) / "finished.txt")
        if finished_flag.exists():
            op.report({'INFO'}, f"PPF finished at frame {frame}")
            PPFSession.cleanup(op)
            return {'FINISHED'}

        return {'PASS_THROUGH'}

    @staticmethod
    def cleanup(op):
        """Terminate any running session and clear operator state."""

        info = getattr(op, "_ppf", None)
        if not info:
            return
        try:
            info["mgr"].clear(force=True)
        except Exception:
            pass
        op._ppf = None
