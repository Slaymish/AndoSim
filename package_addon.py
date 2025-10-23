#!/usr/bin/env python3
"""Create a local Blender add-on package matching the release workflow output."""

from __future__ import annotations

import argparse
import platform
import shutil
import sys
import tempfile
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
ADDON_SRC = REPO_ROOT / "blender_addon"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "dist"

CORE_PATTERNS: tuple[str, ...] = (
    "ando_barrier_core*.so",
    "ando_barrier_core*.pyd",
    "ando_barrier_core*.dll",
    "ando_barrier_core*.dylib",
)


def _default_version() -> str | None:
    version_file = REPO_ROOT / "VERSION"
    if not version_file.exists():
        return None

    raw = version_file.read_text(encoding="utf-8").strip()
    if not raw:
        return None

    return raw if raw.startswith("v") else f"v{raw}"


def _detect_platform() -> str:
    system = sys.platform
    if system.startswith("linux"):
        return "linux_x64"
    if system == "darwin":
        return "macos_universal"
    if system in {"win32", "cygwin"}:
        return "windows_x64"

    raise RuntimeError(f"Unsupported platform '{platform.platform()}'. Please specify --platform.")


def _copy_core_modules(dest_dir: Path) -> list[Path]:
    copied: list[Path] = []
    for pattern in CORE_PATTERNS:
        for candidate in sorted(ADDON_SRC.glob(pattern)):
            target = dest_dir / candidate.name
            shutil.copy2(candidate, target)
            copied.append(target)
    return copied


def _copy_python_sources(dest_dir: Path) -> None:
    for source in sorted(ADDON_SRC.glob("*.py")):
        shutil.copy2(source, dest_dir / source.name)

    manifest = ADDON_SRC / "blender_manifest.toml"
    if not manifest.exists():
        raise FileNotFoundError("blender_manifest.toml not found in blender_addon/")
    shutil.copy2(manifest, dest_dir / manifest.name)


def _zip_directory(source_dir: Path, archive_path: Path) -> None:
    import zipfile

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(source_dir.rglob("*")):
            if file_path.is_dir():
                continue
            relative = file_path.relative_to(source_dir.parent)
            archive.write(file_path, arcname=str(relative))


def _resolve_python_interpreter(args: argparse.Namespace) -> Path | None:
    """Return the interpreter path requested by the user."""

    if args.python and args.python_version:
        raise SystemExit("Specify either --python or --python-version, not both.")

    if args.python:
        path = Path(args.python).expanduser().resolve()
        if not path.exists():
            raise SystemExit(f"Python interpreter not found: {path}")
        return path

    if args.python_version:
        version = args.python_version
        candidates = [
            f"python{version}",
            f"python{version.replace('.', '')}",
            f"python{version}m",
        ]
        for candidate in candidates:
            resolved = shutil.which(candidate)
            if resolved:
                return Path(resolved).resolve()
        raise SystemExit(f"No interpreter matching version {version} was found on PATH.")

    return None


def _venv_python_path(venv_dir: Path) -> Path:
    """Return the python executable inside a virtual environment."""

    if platform.system().lower().startswith("win"):
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _ensure_virtualenv(python: Path, venv_dir: Path) -> Path:
    """Create (or reuse) a virtual environment using the requested interpreter."""

    venv_dir.mkdir(parents=True, exist_ok=True)
    venv_python = _venv_python_path(venv_dir)

    if not venv_python.exists():
        print(f"Creating virtual environment at {venv_dir} with {python} …")
        subprocess.run([str(python), "-m", "venv", str(venv_dir)], check=True)
    else:
        print(f"Reusing virtual environment at {venv_dir}")

    return venv_python


def _install_build_dependencies(python: Path) -> None:
    """Install the Python dependencies required to build the core module."""

    print("Installing build dependencies (pip, numpy, pybind11)…")
    subprocess.run([str(python), "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run(
        [str(python), "-m", "pip", "install", "--upgrade", "numpy", "pybind11[global]>=2.13"],
        check=True,
    )


def _build_core_module(python: Path, clean: bool) -> None:
    """Invoke build.sh with the requested interpreter."""

    build_script = REPO_ROOT / "build.sh"
    if not build_script.exists():
        raise SystemExit(f"build.sh not found at {build_script}")

    cmd: list[str] = [str(build_script)]
    if clean:
        cmd.append("--clean")
    cmd.extend(["--python", str(python)])

    print("Invoking build.sh to compile the native core …")
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version",
        default=_default_version(),
        help="Version string to embed in the archive name (defaults to v<contents of VERSION>).",
    )
    parser.add_argument(
        "--platform",
        default=None,
        help="Platform label (linux_x64, macos_universal, windows_x64). Defaults to auto-detection.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Directory to write the archive into (defaults to {DEFAULT_OUTPUT_DIR}).",
    )
    parser.add_argument(
        "--python",
        default=None,
        help="Path to the Python interpreter that should be used to build the core module.",
    )
    parser.add_argument(
        "--python-version",
        default=None,
        help="Python version (e.g. 3.12) to look up on PATH for building the core module.",
    )
    parser.add_argument(
        "--venv-dir",
        default=None,
        help="Directory to create or reuse the build virtual environment (optional).",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip rebuilding the core module before packaging.",
    )
    parser.add_argument(
        "--clean-build",
        action="store_true",
        help="Pass --clean to build.sh before building.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    python_interpreter = _resolve_python_interpreter(args)
    temp_venv_manager: tempfile.TemporaryDirectory[str] | None = None

    try:
        if not args.skip_build and python_interpreter is not None:
            if args.venv_dir:
                venv_dir = Path(args.venv_dir).expanduser().resolve()
            elif args.python_version:
                version_label = args.python_version.replace(".", "_")
                venv_dir = REPO_ROOT / ".venv" / f"core-build-py{version_label}"
            else:
                temp_venv_manager = tempfile.TemporaryDirectory(prefix="ando_core_env_")
                venv_dir = Path(temp_venv_manager.name)

            venv_python = _ensure_virtualenv(python_interpreter, venv_dir)
            _install_build_dependencies(venv_python)
            _build_core_module(venv_python, args.clean_build)
        elif python_interpreter is not None and args.skip_build:
            print("Python interpreter provided but --skip-build supplied; skipping core rebuild.")
        elif python_interpreter is None and not args.skip_build:
            print("No Python interpreter specified; assuming the native core has already been built.")

        if args.version is None:
            raise SystemExit("Unable to determine version. Pass --version explicitly or create a VERSION file.")

        platform_label = args.platform or _detect_platform()
        if platform_label not in {"linux_x64", "macos_universal", "windows_x64"}:
            raise SystemExit(f"Unknown platform label '{platform_label}'.")

        output_dir = Path(args.output_dir).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        package_name = f"ando_barrier_{args.version}_{platform_label}"
        archive_path = output_dir / f"{package_name}.zip"

        with tempfile.TemporaryDirectory() as tmpdir:
            package_root = Path(tmpdir) / "ando_barrier"
            package_root.mkdir(parents=True, exist_ok=False)

            _copy_python_sources(package_root)
            core_modules = _copy_core_modules(package_root)
            if not core_modules:
                raise SystemExit(
                    "No compiled core module found in blender_addon/. "
                    "Run the build step (or provide --python/--python-version) so the shared library is available."
                )

            _zip_directory(package_root, archive_path)

        print(f"Created {archive_path}")
    finally:
        if temp_venv_manager is not None:
            temp_venv_manager.cleanup()


if __name__ == "__main__":
    main()
