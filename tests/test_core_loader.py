"""Loader regressions isolated from Blender, NumPy, and native binaries."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CoreLoaderTests(unittest.TestCase):
    def setUp(self):
        self.loader = load_file('_loader_test', ROOT / 'blender_addon/_core_loader.py')
        self.modules = patch.dict(sys.modules)
        self.modules.start()
        sys.modules.pop(self.loader._PACKAGE_NAME, None)
        self.addCleanup(self.modules.stop)

    def test_bundled_fallback_precedes_repository_python_shim(self):
        fallback = ROOT / 'blender_addon/ando_barrier_core.py'
        shim = ROOT / 'ando_barrier_core.py'
        expected = types.ModuleType('fallback')
        with patch.object(self.loader, '_iter_candidate_paths', return_value=[fallback]), \
             patch.object(self.loader.importlib.util, 'find_spec', return_value=types.SimpleNamespace(origin=str(shim))), \
             patch.object(self.loader, '_load_module_from_path', return_value=(expected, None)) as load, \
             patch.object(self.loader, '_handle_python_fallback') as notify:
            self.assertIs(self.loader._import_core(), expected)
            load.assert_called_once_with(fallback)
            notify.assert_called_once_with()

    def test_manual_selection_replaces_cached_package_module(self):
        old, new = types.ModuleType('old'), types.ModuleType('new')
        sys.modules[self.loader._PACKAGE_NAME] = old
        self.loader._CACHED_MODULE = old
        with patch.object(self.loader, '_load_module_from_path', return_value=(new, None)):
            self.assertEqual(self.loader.load_core_from_path(Path('native.so')), (new, None))
        self.assertIs(self.loader._import_core(), new)
        self.assertIs(sys.modules[self.loader._PACKAGE_NAME], new)

    def test_background_fallback_does_not_schedule_ui_retry(self):
        bpy = types.SimpleNamespace(app=types.SimpleNamespace(background=True, timers=Mock()),
                                    context=types.SimpleNamespace(window_manager=None))
        with patch.object(self.loader, '_try_import_bpy', return_value=bpy):
            self.loader._handle_python_fallback()
        bpy.app.timers.register.assert_not_called()

    def test_bundled_native_precedes_fallback_and_sys_path(self):
        native = Path('ando_barrier_core.so')
        expected = types.ModuleType('native')
        with patch.object(self.loader, '_iter_candidate_paths', return_value=[native, Path('ando_barrier_core.py')]), \
             patch.object(self.loader, '_load_module_from_path', return_value=(expected, None)) as load, \
             patch.object(self.loader.importlib.util, 'find_spec') as find, \
             patch.object(self.loader, '_handle_python_fallback') as notify:
            self.assertIs(self.loader._import_core(), expected)
            load.assert_called_once_with(native)
            find.assert_not_called()
            notify.assert_not_called()

    def test_installed_native_precedes_bundled_fallback(self):
        native = Path('ando_barrier_core' + importlib.machinery.EXTENSION_SUFFIXES[0])
        expected = types.ModuleType('native')
        with patch.object(self.loader, '_iter_candidate_paths', return_value=[Path('ando_barrier_core.py')]), \
             patch.object(self.loader.importlib.util, 'find_spec', return_value=types.SimpleNamespace(origin=str(native))), \
             patch.object(self.loader, '_load_module_from_path', return_value=(expected, None)) as load:
            self.assertIs(self.loader._import_core(), expected)
            load.assert_called_once_with(native)

    def test_foreign_binary_error_explains_python_minor_requirement(self):
        module, error = self.loader.load_core_from_path(Path('ando_barrier_core.cp311-win_amd64.pyd'))
        self.assertIsNone(module)
        self.assertIn(f'{sys.version_info.major}.{sys.version_info.minor}', error)
        self.assertIn('same Python minor', error)
        self.assertIn('cp311-win_amd64.pyd', error)

    def test_root_shim_loads_sibling_fallback_without_blender(self):
        # NumPy is only needed when using the solver, not defining its API.
        # A module stub keeps this import regression stdlib-only.
        sys.modules['numpy'] = types.ModuleType('numpy')
        with patch.object(__import__('importlib'), 'import_module', side_effect=ModuleNotFoundError('No Blender')):
            module = load_file('_root_shim_test', ROOT / 'ando_barrier_core.py')
        self.assertEqual(module.Material().youngs_modulus, 1.0e6)
        self.assertNotIn('blender_addon', sys.modules)

    def test_package_fallback_works_after_native_load_failure(self):
        package = types.ModuleType('_loader_test_package')
        package.__path__ = [str(ROOT / 'blender_addon')]
        sys.modules[package.__name__] = package
        sys.modules['numpy'] = types.ModuleType('numpy')
        # Bind the loader's default module name inside the synthetic package,
        # rather than changing _PACKAGE_NAME after that default was captured.
        self.loader = load_file(package.__name__ + '._core_loader',
                                ROOT / 'blender_addon/_core_loader.py')
        with patch.object(self.loader, '_iter_candidate_paths', return_value=[
                Path('ando_barrier_core.cp311-win_amd64.pyd'),
                ROOT / 'blender_addon/ando_barrier_core.py']), \
             patch.object(self.loader.importlib.util, 'find_spec', return_value=None), \
             patch.object(self.loader, '_handle_python_fallback') as notify:
            module = self.loader._import_core()
        self.assertEqual(module.Material().youngs_modulus, 1.0e6)
        self.assertEqual(Path(module.__file__), ROOT / 'blender_addon/ando_barrier_core.py')
        self.assertIs(sys.modules[self.loader._PACKAGE_NAME], module)
        notify.assert_called_once_with()



if __name__ == '__main__':
    unittest.main()
