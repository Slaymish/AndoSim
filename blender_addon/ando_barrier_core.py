"""Shim module that exposes the pure-Python fallback implementation."""

from __future__ import annotations

from importlib import import_module
from types import ModuleType


def _load_fallback() -> ModuleType:
    """Load the shared fallback implementation that lives with the add-on."""

    package = __package__ or "ando_barrier"
    try:
        return import_module(f"{package}._core_fallback")
    except ModuleNotFoundError as exc:  # pragma: no cover - defensive
        raise ImportError("Unable to locate fallback implementation for ando_barrier_core") from exc


_FALLBACK = _load_fallback()

# Re-export everything defined by the fallback module so that callers continue
# to interact with the same API surface.
__all__ = getattr(_FALLBACK, "__all__", [])

for _name in dir(_FALLBACK):
    if _name.startswith("__") and _name not in {"__all__"}:
        continue
    globals()[_name] = getattr(_FALLBACK, _name)
