"""Run with the Python environment used by installDevelop; no IDE required."""
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
MODULES = ('clitt', 'datasource', 'firebase', 'hqt', 'hspylib', 'kafman', 'setman', 'vault')


class DevelopInstallTest(unittest.TestCase):
    def gradle(self, *arguments, **environment):
        return subprocess.run(
            [str(ROOT / 'gradlew'), '--offline', '--console=plain', *arguments],
            cwd=ROOT, env={**os.environ, **environment}, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
        )

    def test_all_imports_and_editable_paths_are_local(self):
        for module in MODULES:
            with self.subTest(module=module):
                source = ROOT / 'modules' / module / 'src/main'
                name = 'hspylib' if module == 'hspylib' else 'hspylib-' + module
                distribution = importlib.metadata.distribution(name)
                direct = json.loads(distribution.read_text('direct_url.json'))
                self.assertTrue(direct['dir_info']['editable'])
                self.assertEqual(source.as_uri(), direct['url'])
                result = subprocess.run(
                    [sys.executable, '-c',
                     'import importlib.util; print(importlib.util.find_spec(' + repr(module) + ').origin)'],
                    cwd='/private/tmp', env={k: v for k, v in os.environ.items() if k != 'PYTHONPATH'},
                    capture_output=True, text=True, check=True,
                )
                self.assertTrue(Path(result.stdout.strip()).is_relative_to(source), result.stdout)
                paths = [distribution.locate_file(file).read_text().strip()
                         for file in distribution.files if str(file).endswith('.pth')]
                self.assertIn(str(source), paths)

    def test_develop_alias_installs_workspace_once_without_dependency_upgrade(self):
        result = self.gradle('installDevelop', '--dry-run',
                             '-PpythonExecutable=' + sys.executable,
                             VIRTUAL_ENV='/nonexistent/venv')
        self.assertEqual(0, result.returncode, result.stdout)
        self.assertEqual(1, result.stdout.count(':installDevelop SKIPPED'))
        self.assertNotIn(':installPackages SKIPPED', result.stdout)
        for module in MODULES:
            self.assertIn(':' + module + ':syncRequirements SKIPPED', result.stdout)

    def test_invalid_explicit_interpreter_does_not_fall_back(self):
        result = self.gradle('installDevelop', '--dry-run',
                             '-PpythonExecutable=/nonexistent/python')
        self.assertNotEqual(0, result.returncode)
        self.assertIn('Python executable is unavailable', result.stdout)

    def test_active_virtual_environment_is_used(self):
        result = self.gradle('installDevelop', '--dry-run',
                             VIRTUAL_ENV='/nonexistent/active-venv', PYTHON_EXECUTABLE='')
        self.assertNotEqual(0, result.returncode)
        self.assertIn('/nonexistent/active-venv/bin/python', result.stdout)


if __name__ == '__main__':
    unittest.main()
