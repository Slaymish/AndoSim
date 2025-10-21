"""Compatibility shim that re-exports the add-on's core module."""

from __future__ import annotations

import importlib.util
import sys
from importlib import import_module
from pathlib import Path
from types import ModuleType


def _load_addon_module() -> ModuleType:
    """Import the add-on shim when developing from the repository."""

    try:
        return import_module("blender_addon.ando_barrier_core")
    except ModuleNotFoundError:
        pass

    addon_path = Path(__file__).resolve().with_name("blender_addon") / "ando_barrier_core.py"
    if addon_path.exists():
        spec = importlib.util.spec_from_file_location("_ando_barrier_core_addon_shim", addon_path)
        if spec is not None and spec.loader is not None:  # pragma: no cover - defensive
            module = importlib.util.module_from_spec(spec)
            sys.modules.setdefault("_ando_barrier_core_addon_shim", module)
            spec.loader.exec_module(module)
            return module

    # Fall back to the legacy behaviour where the fallback lived directly next
    # to this file.
    fallback_candidates = [
        Path(__file__).resolve().with_name("blender_addon") / "_core_fallback.py",
        Path(__file__).resolve().with_name("_core_fallback.py"),
    ]

    for candidate in fallback_candidates:
        if not candidate.exists():
            continue

        spec = importlib.util.spec_from_file_location("_ando_barrier_core_fallback", candidate)
        if spec is None or spec.loader is None:  # pragma: no cover - defensive
            continue

        module = importlib.util.module_from_spec(spec)
        sys.modules.setdefault("_ando_barrier_core_fallback", module)
        spec.loader.exec_module(module)
        return module

    raise ImportError("Unable to locate fallback implementation for ando_barrier_core")


_ADDON_MODULE = _load_addon_module()

# Re-export everything defined by the add-on module so existing imports from the
# repository root continue to work without modification.
__all__ = getattr(_ADDON_MODULE, "__all__", [])

for _name in dir(_ADDON_MODULE):
    if _name.startswith("__") and _name not in {"__all__"}:
        continue
    globals()[_name] = getattr(_ADDON_MODULE, _name)
