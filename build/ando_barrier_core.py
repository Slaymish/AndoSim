"""Proxy module that exposes the root-level Python fallback."""

import sys
from importlib import util
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent / "ando_barrier_core.py"
_SPEC = util.spec_from_file_location("_ando_barrier_core_fallback", _ROOT)
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

