"""Shim module that exposes the pure-Python fallback implementation."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load_fallback() -> ModuleType:
    """Load the shared fallback implementation that lives with the add-on."""

    base_path = Path(__file__).resolve().parent
    candidates = [
        base_path / "_core_fallback.py",
        # When developing from the repository root we may still have a copy of
        # the fallback next to the legacy shim.
        base_path.parent / "ando_barrier_core.py",
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

