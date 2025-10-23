#!/usr/bin/env python3
"""Create a local Blender add-on package matching the release workflow output."""

from __future__ import annotations

import argparse
import platform
import shutil
import sys
import tempfile
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()

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
                "Run the build first (./build.sh) so the shared library is available."
            )

        _zip_directory(package_root, archive_path)

    print(f"Created {archive_path}")


if __name__ == "__main__":
    main()
