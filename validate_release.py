#!/usr/bin/env python3
"""
Validate the GitHub Actions built release package.
"""

import sys
import os
from pathlib import Path

def print_status(message, status="info"):
    colors = {
        "info": "\033[0;34m",
        "success": "\033[0;32m",
        "error": "\033[0;31m",
        "warning": "\033[1;33m",
    }
    reset = "\033[0m"
    symbols = {
        "info": "ℹ️",
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
    }
    print(f"{colors[status]}{symbols[status]} {message}{reset}")

def validate_release_package(package_dir):
    """Validate the structure and contents of a release package."""
    
    print("\n" + "="*60)
    print("VALIDATING RELEASE PACKAGE")
    print("="*60 + "\n")
    
    package_path = Path(package_dir)
    if not package_path.exists():
        print_status(f"Package directory not found: {package_dir}", "error")
        return False
    
    print_status(f"Checking package: {package_path.name}", "info")
    
    # Find the ando_barrier subdirectory
    addon_dir = package_path / "ando_barrier"
    if not addon_dir.exists():
        print_status("Missing ando_barrier/ subdirectory", "error")
        return False
    
    print_status("Found ando_barrier/ subdirectory", "success")
    
    # Required files checklist
    required_files = {
        "__init__.py": "Add-on entry point",
        "_core_loader.py": "Core module loader",
        "_core_fallback.py": "Pure Python fallback",
        "ando_barrier_core.py": "Fallback shim",
        "blender_manifest.toml": "Blender 4.2+ manifest",
        "operators.py": "Blender operators",
        "properties.py": "Blender properties",
        "ui.py": "UI panels",
        "visualization.py": "Visualization utilities",
        "create_example_scene.py": "Example scene generator",
        "parameter_update.py": "Parameter update utilities",
    }
    
    # Check for compiled module
    compiled_modules = list(addon_dir.glob("ando_barrier_core*.so")) + \
                      list(addon_dir.glob("ando_barrier_core*.pyd")) + \
                      list(addon_dir.glob("ando_barrier_core*.dylib"))
    
    print("\n" + "-"*60)
    print("FILE CHECK")
    print("-"*60 + "\n")
    
    all_found = True
    for filename, description in required_files.items():
        filepath = addon_dir / filename
        if filepath.exists():
            size = filepath.stat().st_size
            print_status(f"{filename:30} {description:20} ({size:,} bytes)", "success")
        else:
            print_status(f"{filename:30} {description:20} MISSING", "error")
            all_found = False
    
    print()
    if compiled_modules:
        for module in compiled_modules:
            size = module.stat().st_size
            print_status(f"{module.name:30} {'Compiled core':20} ({size:,} bytes)", "success")
            
            # Check execute permissions (Linux/macOS only)
            # Note: While .so files work without +x, it's standard practice to set it
            if sys.platform != "win32":
                if os.access(module, os.X_OK):
                    print_status(f"  → Execute permission: OK (standard)", "success")
                else:
                    print_status(f"  → Execute permission: Not set (still works, but non-standard)", "info")
    else:
        print_status("No compiled module found (.so/.pyd/.dylib)", "error")
        print_status("Package will fall back to pure Python implementation", "warning")
        all_found = False
    
    # Check manifest version
    print("\n" + "-"*60)
    print("MANIFEST CHECK")
    print("-"*60 + "\n")
    
    manifest_path = addon_dir / "blender_manifest.toml"
    if manifest_path.exists():
        with open(manifest_path) as f:
            content = f.read()
            if 'version = "' in content:
                version_line = [line for line in content.split('\n') if 'version = "' in line][0]
                version = version_line.split('"')[1]
                print_status(f"Manifest version: {version}", "info")
            if 'blender_version_min = "' in content:
                blender_line = [line for line in content.split('\n') if 'blender_version_min = "' in line][0]
                blender_ver = blender_line.split('"')[1]
                print_status(f"Minimum Blender: {blender_ver}", "info")
    
    # Check __init__.py
    init_path = addon_dir / "__init__.py"
    if init_path.exists():
        with open(init_path) as f:
            content = f.read()
            if '"version":' in content:
                version_line = [line for line in content.split('\n') if '"version":' in line][0]
                print_status(f"bl_info version: {version_line.strip()}", "info")
    
    # Summary
    print("\n" + "="*60)
    if all_found:
        print_status("VALIDATION PASSED ✓", "success")
        print_status("Package is ready for installation in Blender", "success")
    else:
        print_status("VALIDATION FAILED ✗", "error")
        print_status("Package has missing components", "error")
    print("="*60 + "\n")
    
    return all_found

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate_release.py <path_to_unzipped_package>")
        print("\nExample:")
        print("  python validate_release.py ando_barrier_v1.0.3_linux_x64")
        sys.exit(1)
    
    package_dir = sys.argv[1]
    success = validate_release_package(package_dir)
    sys.exit(0 if success else 1)
