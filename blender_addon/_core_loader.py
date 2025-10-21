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
from typing import Iterable, List

_LOGGER = logging.getLogger(__name__)

_MODULE_NAME = "ando_barrier_core"
_PACKAGE_NAME = f"{__package__}.{_MODULE_NAME}"
_ADDON_ROOT = Path(__file__).resolve().parent

_CACHED_MODULE: ModuleType | None = None
_LOGGED_FAILURE = False


def _ensure_addon_on_path() -> None:
    """Make sure the add-on's directory is present on sys.path."""

    addon_as_str = str(_ADDON_ROOT)
    if addon_as_str not in sys.path:
        sys.path.insert(0, addon_as_str)


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


def _alias_module(module: ModuleType) -> None:
    """Expose the module under both absolute and package-qualified names."""

    sys.modules.setdefault(_MODULE_NAME, module)
    sys.modules.setdefault(_PACKAGE_NAME, module)


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

    _ensure_addon_on_path()

    # Standard import (either native extension on sys.path or already registered).
    try:
        module = importlib.import_module(_MODULE_NAME)
    except ModuleNotFoundError:
        pass
    else:
        _alias_module(module)
        _CACHED_MODULE = module
        return module

    # Package-relative import (pure-Python shim within the add-on).
    try:
        module = importlib.import_module(_PACKAGE_NAME)
    except ModuleNotFoundError:
        pass
    else:
        _alias_module(module)
        _CACHED_MODULE = module
        return module

    errors: List[str] = []
    candidates = list(_iter_candidate_paths())

    for candidate in candidates:
        spec = importlib.util.spec_from_file_location(_MODULE_NAME, candidate)
        if spec is None or spec.loader is None:
            errors.append(f"{candidate}: no loader available")
            continue

        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)  # type: ignore[call-arg]
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(f"{candidate}: {exc}")
            continue

        _alias_module(module)
        _CACHED_MODULE = module
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
