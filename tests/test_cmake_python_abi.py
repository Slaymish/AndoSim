"""Configure-only regression for the explicitly selected Python interpreter ABI."""
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig
import tempfile
import unittest


class CMakePythonABITest(unittest.TestCase):
    def test_explicit_interpreter_controls_module_abi(self):
        self.check_module_abi()

    def test_legacy_cached_suffix_is_replaced(self):
        self.check_module_abi(legacy_cache=True)

    def check_module_abi(self, legacy_cache=False):
        source = Path(__file__).resolve().parents[1]
        pybind_dir = subprocess.check_output(
            [sys.executable, '-m', 'pybind11', '--cmakedir'], text=True
        ).strip()
        with tempfile.TemporaryDirectory(prefix='ando-cmake-abi-') as tmp:
            build = Path(tmp)
            query = build / '.cmake/api/v1/query'
            query.mkdir(parents=True)
            (query / 'codemodel-v2').touch()
            legacy_args = []
            if legacy_cache:
                # Emulate a directory configured with legacy pybind11 discovery.
                legacy_args = [
                    "-DPYTHON_MODULE_EXTENSION:INTERNAL=.cpython-000-stale.so",
                    "-DPYTHON_MODULE_DEBUG_POSTFIX:INTERNAL=",
                    f"-DPYBIND11_PYTHON_EXECUTABLE_LAST:INTERNAL={sys.executable}",
                ]
            result = subprocess.run(
                ['cmake', '-S', str(source), '-B', str(build),
                 '-DBUILD_TESTS=OFF', '-DBUILD_DEMOS=OFF',
                 f'-DPython3_EXECUTABLE={sys.executable}',
                 f'-Dpybind11_DIR={pybind_dir}'] + legacy_args,
                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                env=os.environ.copy(),
            )
            self.assertEqual(result.returncode, 0, result.stdout)
            reply = build / '.cmake/api/v1/reply'
            index = json.loads(next(reply.glob('index-*.json')).read_text())
            model = json.loads((reply / index['reply']['codemodel-v2']['jsonFile']).read_text())
            for config in model['configurations']:
                target = next(t for t in config['targets'] if t['name'] == 'ando_barrier_core')
                data = json.loads((reply / target['jsonFile']).read_text())
                names = [Path(a['path']).name for a in data['artifacts']]
                expected = 'ando_barrier_core' + sysconfig.get_config_var('EXT_SUFFIX')
                self.assertIn(expected, names, result.stdout)


if __name__ == '__main__':
    unittest.main()
