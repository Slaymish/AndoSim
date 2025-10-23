"""Utilities for locating and importing the ``ando_barrier_core`` module.

The add-on expects the native extension (``ando_barrier_core``) to live alongside
the package when it is bundled for Blender. During development the module might
also be available on the Python path or replaced by the pure-Python fallback.

This helper centralises the import logic so callers do not have to reach into
Blender's ``scripts/`` directory directly and receive a consistent error message
if the core module cannot be found.
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from types import ModuleType
from typing import Iterable, List, Optional

_LOGGER = logging.getLogger(__name__)

_MODULE_NAME = "ando_barrier_core"
_PACKAGE_PREFIX = __package__ or "ando_barrier"
_PACKAGE_NAME = f"{_PACKAGE_PREFIX}.{_MODULE_NAME}"
_ADDON_ROOT = Path(__file__).resolve().parent

_CACHED_MODULE: ModuleType | None = None
_LOGGED_FAILURE = False
_FALLBACK_PROMPTED = False


def _iter_candidate_paths() -> Iterable[Path]:
    """Yield candidate files that could implement ``ando_barrier_core``."""

    patterns = [
        "ando_barrier_core*.so",
        "ando_barrier_core*.pyd",
        "ando_barrier_core*.dll",
        "ando_barrier_core*.dylib",
    ]

    for pattern in patterns:
        for path in sorted(_ADDON_ROOT.glob(pattern)):
            yield path

    fallback_py = _ADDON_ROOT / "ando_barrier_core.py"
    if fallback_py.exists():
        yield fallback_py


def _register_package_module(module: ModuleType) -> None:
    """Ensure the resolved module is available under the package namespace."""

    sys.modules.setdefault(_PACKAGE_NAME, module)


def _load_module_from_path(path: Path, *, module_name: str = _PACKAGE_NAME) -> tuple[ModuleType | None, str | None]:
    """Load a module directly from the provided file system path."""

    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
    except Exception as exc:  # pragma: no cover - defensive
        return None, str(exc)

    if spec is None or spec.loader is None:
        return None, "no loader available"

    try:
        module = importlib.util.module_from_spec(spec)
    except Exception as exc:  # pragma: no cover - defensive
        return None, str(exc)

    try:
        spec.loader.exec_module(module)  # type: ignore[call-arg]
    except Exception as exc:  # pragma: no cover - defensive
        return None, str(exc)

    return module, None


def _import_core() -> ModuleType:
    """Internal helper that tries every resolution strategy and returns the module.

    Raises
    ------
    ImportError
        If no import strategy succeeds.
    """

    global _CACHED_MODULE  # pylint: disable=global-statement

    if _CACHED_MODULE is not None:
        return _CACHED_MODULE

    preloaded = sys.modules.get(_PACKAGE_NAME)
    if preloaded is not None:
        _CACHED_MODULE = preloaded
        return preloaded

    errors: List[str] = []
    candidates = list(_iter_candidate_paths())
    fallback_candidate: Path | None = None

    for candidate in candidates:
        suffix = candidate.suffix.lower()
        if suffix == ".py":
            fallback_candidate = candidate
            continue

        module, error = _load_module_from_path(candidate)
        if module is None:
            errors.append(f"{candidate}: {error}")
            continue

        _register_package_module(module)
        _CACHED_MODULE = module
        return module

    # Try to re-use an installed wheel/egg without polluting sys.path.
    spec = importlib.util.find_spec(_MODULE_NAME)
    if spec and spec.origin:
        module_path = Path(spec.origin)
        module, error = _load_module_from_path(module_path)
        if module is None:
            errors.append(f"{module_path}: {error}")
        else:
            _register_package_module(module)
            _CACHED_MODULE = module
            return module

    if fallback_candidate is not None:
        module, error = _load_module_from_path(fallback_candidate)
        if module is None:
            errors.append(f"{fallback_candidate}: {error}")
        else:
            _register_package_module(module)
            _CACHED_MODULE = module
            _handle_python_fallback()
            return module

    # Package-relative import (pure-Python shim within the add-on).
    try:
        module = importlib.import_module(_PACKAGE_NAME)
    except ModuleNotFoundError:
        module = None
    else:
        _register_package_module(module)
        _CACHED_MODULE = module
        _handle_python_fallback()
        return module

    search_hint = ", ".join(str(path) for path in candidates) or "no matching files"
    error_details = "; ".join(errors) if errors else "no additional diagnostics"
    raise ImportError(
        f"Unable to locate '{_MODULE_NAME}'. "
        f"Tried sys.path, '{_PACKAGE_NAME}', and checked {_ADDON_ROOT}. "
        f"Candidates: {search_hint}. Details: {error_details}."
    )


def _log_failure(message: str, exc: Exception) -> None:
    """Log the import failure once and provide a console hint."""

    global _LOGGED_FAILURE  # pylint: disable=global-statement
    if not _LOGGED_FAILURE:
        _LOGGER.error(message)
        _LOGGER.debug("ando_barrier_core import failure", exc_info=exc)
        print(f"[Ando Barrier] {message}", file=sys.stderr)
        _LOGGED_FAILURE = True


def get_core_module(
    *,
    reporter=None,
    report_level: str = "ERROR",
    context: str | None = None,
    strict: bool = False,
) -> ModuleType | None:
    """Return the resolved ``ando_barrier_core`` module or ``None`` on failure.

    Parameters
    ----------
    reporter:
        Optional Blender reporter callable (e.g. ``self.report``). When provided,
        the helper calls it with ``{report_level}`` and a concise message if the
        core cannot be imported.
    report_level:
        Set the severity passed to ``reporter``. Typical values are ``'ERROR'``,
        ``'WARNING'`` or ``'INFO'``.
    context:
        Additional text appended to the diagnostic message so the caller can
        explain why the core module was required.
    strict:
        If ``True``, re-raise the underlying ``ImportError`` after logging. When
        ``False`` (default) the helper swallows the error and returns ``None``.
    """

    try:
        return _import_core()
    except ImportError as exc:  # pragma: no cover - exercised in Blender runtime
        base_message = (
            "ando_barrier_core module not found. "
            "Ensure the add-on bundle includes the compiled core or build it with ./build.sh."
        )
        if context:
            message = f"{base_message} Context: {context}"
        else:
            message = base_message

        _log_failure(message, exc)

        if reporter is not None:
            try:
                reporter({report_level}, message)
            except Exception:  # pragma: no cover - defensive (reporter is Blender API)
                _LOGGER.debug("Reporter callback failed", exc_info=True)

        if strict:
            raise

        return None


def core_available() -> bool:
    """Return ``True`` when the core module can be imported successfully."""

    try:
        _import_core()
    except ImportError:
        return False
    return True


def load_core_from_path(path: Path) -> tuple[ModuleType | None, str | None]:
    """Load a compiled core module from ``path`` and cache it for future calls."""

    module, error = _load_module_from_path(path)
    if module is None:
        return None, error

    _register_package_module(module)

    global _CACHED_MODULE  # pylint: disable=global-statement
    _CACHED_MODULE = module

    return module, None


def _handle_python_fallback() -> None:
    """Notify Blender users that the Python fallback is active and prompt selection."""

    global _FALLBACK_PROMPTED  # pylint: disable=global-statement
    if _FALLBACK_PROMPTED:
        return

    _FALLBACK_PROMPTED = True

    bpy = _try_import_bpy()
    if bpy is None:
        return

    def _prompt_user() -> Optional[float]:  # pragma: no cover - Blender UI interaction
        window_manager = getattr(bpy.context, "window_manager", None)
        if window_manager is None:
            return 0.5

        def _draw(self, _context):
            self.layout.label(text="Core module not found.")
            self.layout.label(text="Please select it manually to enable full performance.")

        try:
            window_manager.popup_menu(_draw, title="Ando Barrier Core", icon='ERROR')
        except Exception:  # pragma: no cover - defensive: Blender UI quirks
            _LOGGER.debug("Failed to display fallback popup", exc_info=True)

        try:
            bpy.ops.ando.select_core_module('INVOKE_DEFAULT')
        except Exception:  # pragma: no cover - operator may not be registered yet
            _LOGGER.debug("Manual core selection operator unavailable, retrying", exc_info=True)
            return 0.5

        return None

    try:
        bpy.app.timers.register(_prompt_user, first_interval=0.1)
    except Exception:  # pragma: no cover - defensive: timers not available
        _LOGGER.debug("Failed to register fallback timer", exc_info=True)


def _try_import_bpy():
    """Safely attempt to import :mod:`bpy` without raising on failure."""

    try:  # pragma: no cover - Blender-specific
        import bpy  # type: ignore
    except ModuleNotFoundError:  # pragma: no cover - executed outside Blender
        return None
    except Exception:  # pragma: no cover - defensive
        _LOGGER.debug("Unexpected failure importing bpy", exc_info=True)
        return None

    return bpy


if __name__ == "__main__":  # Quick test when executed directly.
    try:
        core = _import_core()
    except ImportError as err:
        print(f"Import failed: {err}")
    else:
        print(f"Imported core module: {core}")
