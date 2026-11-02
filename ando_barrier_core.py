"""Compatibility shim that re-exports the bundled Python fallback."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load_addon_module() -> ModuleType:
    """Load the bundled fallback without initializing the Blender add-on."""

    # Load the implementation directly: importing the add-on package executes
    # Blender-only initialization, and a standalone add-on shim has no package
    # context for its relative fallback import.
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
        sys.modules["_ando_barrier_core_fallback"] = module
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
