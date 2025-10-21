"""Shim module that exposes the pure-Python fallback implementation."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load_fallback() -> ModuleType:
    """Load the shared fallback implementation from the add-on sources."""

    # Candidates are checked in order.  The first is used when running the unit
    # tests from the repository root, while the second allows the fallback file
    # to live next to this shim when packaged outside of the Blender add-on.
    candidates = [
        Path(__file__).resolve().with_name("blender_addon") / "_core_fallback.py",
        Path(__file__).resolve().with_name("_core_fallback.py"),
    ]

    for candidate in candidates:
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


_FALLBACK = _load_fallback()

# Re-export everything defined by the fallback module so that callers continue
# to interact with the same API surface.
__all__ = getattr(_FALLBACK, "__all__", [])

for _name in dir(_FALLBACK):
    if _name.startswith("__") and _name not in {"__all__"}:
        continue
    globals()[_name] = getattr(_FALLBACK, _name)

