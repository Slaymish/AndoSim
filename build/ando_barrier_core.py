"""Proxy module that exposes the shared Python fallback implementation."""

import sys
from importlib import util
from pathlib import Path

_CANDIDATES = [
    Path(__file__).resolve().parent / "_core_fallback.py",
    Path(__file__).resolve().parent.parent / "blender_addon" / "_core_fallback.py",
    Path(__file__).resolve().parent.parent / "ando_barrier_core.py",
]

_SPEC = None
for _candidate in _CANDIDATES:
    if not _candidate.exists():
        continue
    _SPEC = util.spec_from_file_location("_ando_barrier_core_fallback", _candidate)
    if _SPEC is not None and _SPEC.loader is not None:
        break

if _SPEC is None or _SPEC.loader is None:  # pragma: no cover - defensive
    raise ImportError("Unable to locate Python fallback for ando_barrier_core")

_MODULE = util.module_from_spec(_SPEC)
sys.modules.setdefault("_ando_barrier_core_fallback", _MODULE)
_SPEC.loader.exec_module(_MODULE)

__all__ = getattr(_MODULE, "__all__", [])

for _name in dir(_MODULE):
    if _name.startswith("__") and _name not in {"__all__"}:
        continue
    globals()[_name] = getattr(_MODULE, _name)

