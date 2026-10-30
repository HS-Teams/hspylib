"""Exercise the real CLI, including startup and parser logging, in isolated processes."""
import base64
import os
import subprocess
import sys
import unittest
import tempfile
from pathlib import Path
from _security_test_setup import setup_sources
setup_sources()

class TestVaultCliSecurity(unittest.TestCase):

    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='vault-security-')
        self.addCleanup(directory.cleanup)
        self.temp_path = Path(directory.name)

    def test_rejected_arguments_never_echo_passwords_add(self):
        arguments = ['add', 'entry', 'hint', 'rejected-secret']
        encoded = base64.b64encode(b'configured-master-secret').decode()
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path), HHS_VAULT_FILE=str(self.temp_path / 'secret.vault'), HHS_VAULT_USER='alice', HHS_VAULT_PASSPHRASE=encoded, HHS_LOG_DIR=str(self.temp_path), ACTIVE_PROFILE='')
        result = subprocess.run([sys.executable, '-m', 'vault', *arguments], env=env, cwd=self.temp_path, capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr + ''.join((path.read_text() for path in self.temp_path.glob('*.log')))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Invalid argument', output)
        for secret in ('rejected-secret', 'configured-master-secret', encoded):
            self.assertNotIn(secret, output)
        self.assertFalse((self.temp_path / 'secret.vault').exists())

    def test_rejected_arguments_never_echo_passwords_update(self):
        arguments = ['upd', 'entry', 'hint', 'rejected-secret']
        encoded = base64.b64encode(b'configured-master-secret').decode()
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path), HHS_VAULT_FILE=str(self.temp_path / 'secret.vault'), HHS_VAULT_USER='alice', HHS_VAULT_PASSPHRASE=encoded, HHS_LOG_DIR=str(self.temp_path), ACTIVE_PROFILE='')
        result = subprocess.run([sys.executable, '-m', 'vault', *arguments], env=env, cwd=self.temp_path, capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr + ''.join((path.read_text() for path in self.temp_path.glob('*.log')))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Invalid argument', output)
        for secret in ('rejected-secret', 'configured-master-secret', encoded):
            self.assertNotIn(secret, output)
        self.assertFalse((self.temp_path / 'secret.vault').exists())

    def test_rejected_arguments_never_echo_passwords_unknown_command(self):
        arguments = ['rejected-secret']
        encoded = base64.b64encode(b'configured-master-secret').decode()
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path), HHS_VAULT_FILE=str(self.temp_path / 'secret.vault'), HHS_VAULT_USER='alice', HHS_VAULT_PASSPHRASE=encoded, HHS_LOG_DIR=str(self.temp_path), ACTIVE_PROFILE='')
        result = subprocess.run([sys.executable, '-m', 'vault', *arguments], env=env, cwd=self.temp_path, capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr + ''.join((path.read_text() for path in self.temp_path.glob('*.log')))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Invalid argument', output)
        for secret in ('rejected-secret', 'configured-master-secret', encoded):
            self.assertNotIn(secret, output)
        self.assertFalse((self.temp_path / 'secret.vault').exists())

    def test_config_file_values_are_redacted_during_real_application_startup(self):
        resources = self.temp_path / 'resources'
        resources.mkdir()
        secret = 'encoded-config-file-secret'
        (resources / 'application.properties').write_text(f"hhs.vault.file={self.temp_path / 'secret.vault'}\nhhs.vault.user=alice\nhhs.vault.passphrase={secret}\n")
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path), HHS_LOG_DIR=str(self.temp_path), ACTIVE_PROFILE='')
        for name in ('HHS_VAULT_FILE', 'HHS_VAULT_USER', 'HHS_VAULT_PASSPHRASE'):
            env.pop(name, None)
        code = "import sys; from vault.__main__ import Main; Main.RESOURCE_DIR=sys.argv[1]; Main('vault').run(['list'])"
        result = subprocess.run([sys.executable, '-c', code, str(resources)], env=env, cwd=self.temp_path, capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr + ''.join((path.read_text() for path in self.temp_path.glob('*.log')))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Remove hhs.vault.passphrase', output)
        self.assertNotIn(secret, output)
if __name__ == '__main__':
    unittest.main()
