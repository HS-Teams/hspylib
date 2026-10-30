"""Exercise the shared publish task with local Git repositories and a fake uploader."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
MODULES = ('clitt', 'datasource', 'firebase', 'hqt', 'hspylib', 'kafman', 'setman', 'vault')


class PublishTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hspylib-publish-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Publish Test')
        self.git('commit', '--allow-empty', '-qm', 'Fixture')
        subprocess.run(['git', 'init', '--bare', '-q', str(self.root / 'remote.git')], check=True)
        self.git('remote', 'add', 'origin', str(self.root / 'remote.git'))
        (self.repo / 'settings.gradle').write_text(
            "rootProject.name = 'publish-test'\ninclude " + ', '.join(repr(m) for m in MODULES))
        uploader = self.repo / 'uploader'
        uploader.write_text('#!/bin/sh\nif [ "$3" = upload ]; then echo upload >> "' +
                            str(self.repo / 'uploads') + '"; fi\n')
        uploader.chmod(0o755)
        script = json.dumps(str(ROOT / 'gradle/pypi-publish.gradle'))
        (self.repo / 'build.gradle').write_text('''
subprojects {
  ext.sourceRoot = "${projectDir}/src"
  ext.versionFile = "${sourceRoot}/main/.version"
  ext.app_version = '0.9.153'
  ext.python = rootProject.file('uploader').absolutePath
  tasks.register('patchVersion') {
    doLast { file(versionFile).text = '0.9.154' }
  }
  tasks.register('syncRequirements')
  apply from: SCRIPT
  tasks.named('sdist') { actions.clear() }
}
'''.replace('SCRIPT', script))
        for module in MODULES:
            source = self.repo / module / 'src/main'
            source.mkdir(parents=True)
            (source / 'setup.py').touch()
            (source / '.version').write_text('0.9.153')
            self.assertIn('pypi-publish.gradle', (ROOT / 'modules' / module / 'build.gradle').read_text())

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.repo, check=True,
                              capture_output=True, text=True).stdout.strip()

    def publish(self, *args):
        return subprocess.run([str(ROOT / 'gradlew'), '-p', str(self.repo),
                               '--offline', '--console=plain', *args],
                              capture_output=True, text=True)

    def test_all_modules_use_updated_version_and_distinct_tags(self):
        self.git('tag', 'v0.9.153')
        result = self.publish('publish')
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        for module in MODULES:
            self.assertTrue(self.git('ls-remote', '--tags', 'origin',
                                     'refs/tags/' + module + '-v0.9.154'))
            self.assertEqual('', self.git('tag', '-l', module + '-v0.9.153'))
        self.assertEqual(8, len((self.repo / 'uploads').read_text().splitlines()))

    def test_local_collision_blocks_upload(self):
        self.git('tag', 'clitt-v0.9.154')
        result = self.publish(':clitt:publish')
        self.assertNotEqual(0, result.returncode)
        self.assertIn('already exists locally', result.stderr)
        self.assertFalse((self.repo / 'uploads').exists())

    def test_remote_collision_blocks_upload(self):
        self.git('tag', 'vault-v0.9.154')
        self.git('push', 'origin', 'refs/tags/vault-v0.9.154')
        self.git('tag', '-d', 'vault-v0.9.154')
        result = self.publish(':vault:publish')
        self.assertNotEqual(0, result.returncode)
        self.assertIn('already exists on origin', result.stderr)
        self.assertFalse((self.repo / 'uploads').exists())

    def test_no_patch_uses_current_version(self):
        result = self.publish(':clitt:publish', '-Pno-patch=true')
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual('clitt-v0.9.153', self.git('tag', '-l'))

    def test_unreachable_remote_blocks_upload(self):
        self.git('remote', 'set-url', 'origin', str(self.root / 'missing.git'))
        result = self.publish(':clitt:publish')
        self.assertNotEqual(0, result.returncode)
        self.assertFalse((self.repo / 'uploads').exists())


if __name__ == '__main__':
    unittest.main()
