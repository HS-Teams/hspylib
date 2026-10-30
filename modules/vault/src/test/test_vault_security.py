"""Security regressions using synthetic secrets and real cryptographic operations."""
import base64
import logging
import os
import sqlite3
import stat
import subprocess
import sys
import warnings
from pathlib import Path
import cryptocode
from cryptography.fernet import InvalidToken
import unittest
import tempfile
import io
from unittest.mock import patch
from _security_test_setup import setup_sources
setup_sources()
from hspylib.modules.security.security import encode_file, encrypt_file
from vault.core.vault import Vault
from vault.core.vault_cipher import VaultCipher
from vault.exception.exceptions import VaultAuthenticationError, VaultSecurityException
MASTER = 'synthetic master passphrase'
SECRET = 'synthetic-entry-secret-\'"-ç'
LEGACY_KEY = 'e4f362fd1e02df6bc9c684c9310e3550'

def write_legacy(path, count=1, key=LEGACY_KEY, corrupt=False, master=MASTER):
    """Use the old public writer, independently of the new migration implementation."""
    database = path.with_suffix('.fixture.sqlite')
    conn = sqlite3.connect(database)
    conn.execute('CREATE TABLE VAULT_ENTRIES (uuid TEXT PRIMARY KEY, key TEXT UNIQUE NOT NULL, name TEXT NOT NULL, password TEXT NOT NULL, hint TEXT NOT NULL, modified TEXT NOT NULL)')
    encrypted = cryptocode.encrypt(SECRET, key)
    conn.executemany('INSERT INTO VAULT_ENTRIES VALUES (?, ?, ?, ?, ?, ?)', [(str(i), f'key-{i}', f'name-{i}', 'broken' if corrupt else encrypted, 'hint', '2024-01-01') for i in range(count)])
    conn.commit()
    conn.close()
    encoded = path.with_suffix('.fixture.encoded')
    encode_file(str(database), str(encoded), binary=True)
    encrypt_file(str(encoded), str(path), 'alice:' + master)
    database.unlink()
    encoded.unlink()
    return (path.read_bytes(), encrypted)

def add_entry(vault, name='entry', secret=SECRET):
    vault.add(name, 'synthetic hint', secret)

class TestVaultSecurity(unittest.TestCase):

    def patch_target(self, target, replacement):
        patcher = patch(target, replacement)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def set_environment(self, name, value):
        patcher = patch.dict(os.environ, {name: value})
        self.addCleanup(patcher.stop)
        patcher.start()

    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='vault-security-')
        self.addCleanup(directory.cleanup)
        self.temp_path = Path(directory.name)
        names = {'HHS_VAULT_FILE', 'HHS_VAULT_USER', 'HHS_VAULT_PASSPHRASE', 'ACTIVE_PROFILE', 'VAULT_HASHCODE'}
        environment = {name: value for (name, value) in os.environ.items() if name not in names}
        patcher = patch.dict(os.environ, environment, clear=True)
        self.addCleanup(patcher.stop)
        patcher.start()
        self.patch_target('vault.core.vault.getpass.getpass', lambda prompt: MASTER)
        self.patch_target('vault.core.vault.sysout', lambda *args: None)
        self.counter = 0

    def make_vault(self, name='secrets.vault', configured_password=''):
        self.counter += 1
        resources = self.temp_path / f'resources-{self.counter}'
        resources.mkdir()
        path = self.temp_path / name
        (resources / 'application.properties').write_text(f'hhs.vault.file={path}\nhhs.vault.user=alice\nhhs.vault.passphrase={configured_password}\n')
        return (Vault(str(resources)), path)

    def capture_logs(self, level):
        self.log_output = io.StringIO()
        logger = logging.getLogger()
        self.addCleanup(logger.setLevel, logger.level)
        handler = logging.StreamHandler(self.log_output)
        self.addCleanup(handler.close)
        self.addCleanup(logger.removeHandler, handler)
        logger.addHandler(handler)
        logger.setLevel(level)

    def test_new_vault_roundtrip_and_private_work_files(self):
        (vault, path) = self.make_vault()
        old_umask = os.umask(18)
        try:
            with vault.open():
                add_entry(vault)
                work = Path(vault.service.repository.database)
                self.assertEqual(stat.S_IMODE(work.stat().st_mode), 384)
                self.assertEqual(stat.S_IMODE(work.parent.stat().st_mode), 448)
                self.assertNotIn(SECRET.encode(), work.read_bytes())
                self.assertFalse(path.exists())
                self.assertFalse(Path(str(path) + '.unlocked').exists())
        finally:
            os.umask(old_umask)
        self.assertFalse(work.parent.exists())
        self.assertTrue(path.read_bytes().startswith(VaultCipher.MAGIC))
        self.assertNotIn(SECRET.encode(), path.read_bytes())
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 384)
        self.assertEqual(stat.S_IMODE(Path(str(path) + '.lock').stat().st_mode), 384)
        (reopened, _) = self.make_vault()
        with reopened.open():
            entry = reopened.service.get_by_key('entry')
            self.assertEqual(reopened._decrypt_passphrase(entry.password), SECRET)
            self.assertIs(cryptocode.decrypt(entry.password, LEGACY_KEY), False)

    def test_keys_and_salts_are_independent_between_vaults(self):
        (first, _) = self.make_vault('first.vault')
        (second, _) = self.make_vault('second.vault')
        with first.open(), second.open():
            add_entry(first)
            add_entry(second)
            self.assertNotEqual(first._entry_key, second._entry_key)
            self.assertNotEqual(first._cipher.salt, second._cipher.salt)
            with self.assertRaises(InvalidToken):
                second._decrypt_passphrase(first.service.get_by_key('entry').password)

    def test_migration_preserves_every_entry_and_original_backup(self):
        (vault, path) = self.make_vault()
        (original, old_ciphertext) = write_legacy(path, count=502)
        with vault.open():
            entries = vault.service.list()
            self.assertEqual(len(entries), 502)
            self.assertEqual(path.read_bytes(), original)
            for entry in entries:
                self.assertEqual(vault._decrypt_passphrase(entry.password), SECRET)
                self.assertEqual(entry.modified, '2024-01-01')
            self.assertNotIn(old_ciphertext.encode(), vault.service.repository.snapshot())
        backup = Path(str(path) + '.legacy.bak')
        self.assertEqual(backup.read_bytes(), original)
        self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 384)
        (reopened, _) = self.make_vault()
        with reopened.open():
            self.assertEqual(len(reopened.service.list()), 502)
        self.assertEqual(backup.read_bytes(), original)

    def test_custom_legacy_key_is_supported_only_for_migration(self):
        (vault, path) = self.make_vault()
        (original, _) = write_legacy(path, key='custom legacy key')
        with self.assertRaisesRegex(VaultSecurityException, 'Legacy entry decryption failed'):
            with vault.open():
                self.fail('Wrong legacy key must not open')
        self.assertEqual(path.read_bytes(), original)
        self.set_environment('VAULT_HASHCODE', 'custom legacy key')
        with vault.open():
            self.assertEqual(vault._decrypt_passphrase(vault.service.get_by_key('key-0').password), SECRET)
        self.set_environment('VAULT_HASHCODE', 'different and irrelevant now')
        with vault.open():
            self.assertEqual(vault._decrypt_passphrase(vault.service.get_by_key('key-0').password), SECRET)

    def test_wrong_master_password_preserves_original_current_format(self):
        legacy = False
        (vault, path) = self.make_vault()
        if legacy:
            write_legacy(path)
        else:
            with vault.open():
                add_entry(vault)
        original = path.read_bytes()
        self.patch_target('vault.core.vault.getpass.getpass', lambda prompt: 'wrong password')
        with self.assertRaises(VaultAuthenticationError):
            with vault.open():
                self.fail('Wrong master password must not open')
        self.assertEqual(path.read_bytes(), original)
        self.assertIs(vault._storage, None)
        self.assertIs(vault._entry_key, None)
        self.assertFalse(Path(str(path) + '.legacy.bak').exists())

    def test_wrong_master_password_preserves_original_legacy_format(self):
        legacy = True
        (vault, path) = self.make_vault()
        if legacy:
            write_legacy(path)
        else:
            with vault.open():
                add_entry(vault)
        original = path.read_bytes()
        self.patch_target('vault.core.vault.getpass.getpass', lambda prompt: 'wrong password')
        with self.assertRaises(VaultAuthenticationError):
            with vault.open():
                self.fail('Wrong master password must not open')
        self.assertEqual(path.read_bytes(), original)
        self.assertIs(vault._storage, None)
        self.assertIs(vault._entry_key, None)
        self.assertFalse(Path(str(path) + '.legacy.bak').exists())

    def test_tampered_vault_never_replaced_magic(self):
        offset = 0
        (vault, path) = self.make_vault()
        with vault.open():
            add_entry(vault)
        damaged = bytearray(path.read_bytes())
        damaged[offset] ^= 1
        path.write_bytes(damaged)
        with self.assertRaises(VaultAuthenticationError):
            with vault.open():
                self.fail('Damaged vault must not open')
        self.assertEqual(path.read_bytes(), damaged)

    def test_tampered_vault_never_replaced_header(self):
        offset = len(VaultCipher.MAGIC)
        (vault, path) = self.make_vault()
        with vault.open():
            add_entry(vault)
        damaged = bytearray(path.read_bytes())
        damaged[offset] ^= 1
        path.write_bytes(damaged)
        with self.assertRaises(VaultAuthenticationError):
            with vault.open():
                self.fail('Damaged vault must not open')
        self.assertEqual(path.read_bytes(), damaged)

    def test_tampered_vault_never_replaced_payload(self):
        offset = -10
        (vault, path) = self.make_vault()
        with vault.open():
            add_entry(vault)
        damaged = bytearray(path.read_bytes())
        damaged[offset] ^= 1
        path.write_bytes(damaged)
        with self.assertRaises(VaultAuthenticationError):
            with vault.open():
                self.fail('Damaged vault must not open')
        self.assertEqual(path.read_bytes(), damaged)

    def test_invalid_legacy_entry_aborts_without_backup_or_overwrite(self):
        (vault, path) = self.make_vault()
        (original, _) = write_legacy(path, corrupt=True)
        with self.assertRaises(VaultSecurityException):
            with vault.open():
                self.fail('Invalid legacy entry must not migrate')
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse(Path(str(path) + '.legacy.bak').exists())

    def test_interrupted_operation_discards_changes_and_cleans_up_runtime_error(self):
        failure = RuntimeError
        (vault, path) = self.make_vault()
        with vault.open():
            add_entry(vault)
        original = path.read_bytes()
        with self.assertRaises(failure):
            with vault.open():
                work = Path(vault.service.repository.database)
                add_entry(vault, 'discard-me')
                raise failure()
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse(work.parent.exists())
        with self.assertRaisesRegex(VaultSecurityException, 'locked'):
            vault.service.list()

    def test_interrupted_operation_discards_changes_and_cleans_up_keyboard_interrupt(self):
        failure = KeyboardInterrupt
        (vault, path) = self.make_vault()
        with vault.open():
            add_entry(vault)
        original = path.read_bytes()
        with self.assertRaises(failure):
            with vault.open():
                work = Path(vault.service.repository.database)
                add_entry(vault, 'discard-me')
                raise failure()
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse(work.parent.exists())
        with self.assertRaisesRegex(VaultSecurityException, 'locked'):
            vault.service.list()

    def test_interrupted_operation_discards_changes_and_cleans_up_system_exit(self):
        failure = SystemExit
        (vault, path) = self.make_vault()
        with vault.open():
            add_entry(vault)
        original = path.read_bytes()
        with self.assertRaises(failure):
            with vault.open():
                work = Path(vault.service.repository.database)
                add_entry(vault, 'discard-me')
                raise failure()
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse(work.parent.exists())
        with self.assertRaisesRegex(VaultSecurityException, 'locked'):
            vault.service.list()

    def test_failed_atomic_replace_preserves_original_and_verified_backup(self):
        (vault, path) = self.make_vault()
        (original, _) = write_legacy(path)

        def fail_replace(*args, **kwargs):
            raise OSError('simulated disk failure')
        self.patch_target('vault.core.vault_storage.os.replace', fail_replace)
        with self.assertRaisesRegex(OSError, 'simulated'):
            with vault.open():
                work = Path(vault.service.repository.database)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(Path(str(path) + '.legacy.bak').read_bytes(), original)
        self.assertFalse(work.parent.exists())
        self.assertFalse(list(path.parent.glob('.vault-*.tmp')))

    def test_symlink_targets_are_never_read_or_overwritten_vault(self):
        suffix = ''
        (vault, path) = self.make_vault()
        target = path.parent / 'unrelated'
        target.write_bytes(b'unrelated contents')
        if suffix == '.legacy.bak':
            write_legacy(path)
        Path(str(path) + suffix).symlink_to(target)
        with self.assertRaises((OSError, VaultSecurityException)):
            with vault.open():
                pass
        self.assertEqual(target.read_bytes(), b'unrelated contents')

    def test_symlink_targets_are_never_read_or_overwritten_lock(self):
        suffix = '.lock'
        (vault, path) = self.make_vault()
        target = path.parent / 'unrelated'
        target.write_bytes(b'unrelated contents')
        if suffix == '.legacy.bak':
            write_legacy(path)
        Path(str(path) + suffix).symlink_to(target)
        with self.assertRaises((OSError, VaultSecurityException)):
            with vault.open():
                pass
        self.assertEqual(target.read_bytes(), b'unrelated contents')

    def test_symlink_targets_are_never_read_or_overwritten_backup(self):
        suffix = '.legacy.bak'
        (vault, path) = self.make_vault()
        target = path.parent / 'unrelated'
        target.write_bytes(b'unrelated contents')
        if suffix == '.legacy.bak':
            write_legacy(path)
        Path(str(path) + suffix).symlink_to(target)
        with self.assertRaises((OSError, VaultSecurityException)):
            with vault.open():
                pass
        self.assertEqual(target.read_bytes(), b'unrelated contents')

    def test_legacy_residue_and_conflicting_backups_are_preserved(self):
        (vault, path) = self.make_vault()
        (original, _) = write_legacy(path)
        residue = Path(str(path) + '.unlocked')
        residue.write_bytes(b'recover me')
        with self.assertRaisesRegex(VaultSecurityException, 'manual recovery'):
            with vault.open():
                pass
        self.assertEqual(residue.read_bytes(), b'recover me')
        residue.unlink()
        backup = Path(str(path) + '.legacy.bak')
        backup.write_bytes(b'other backup')
        with self.assertRaisesRegex(VaultSecurityException, 'different contents'):
            with vault.open():
                pass
        self.assertEqual(backup.read_bytes(), b'other backup')
        self.assertEqual(path.read_bytes(), original)

    def test_second_process_cannot_open_locked_vault(self):
        (vault, path) = self.make_vault()
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path))
        code = 'import sys; from vault.core.vault_storage import VaultStorage; s=VaultStorage(sys.argv[1]); s.acquire()'
        with vault.open():
            result = subprocess.run([sys.executable, '-c', code, str(path)], env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('already open', result.stderr)

    def test_sql_injection_and_quoted_values_are_data(self):
        (vault, _) = self.make_vault()
        name = 'entry\'"; DROP TABLE VAULT_ENTRIES;--'
        with vault.open():
            add_entry(vault, name)
            payload = "' UNION SELECT uuid,password,name,password,hint,modified FROM VAULT_ENTRIES -- "
            self.assertEqual(vault.service.list_by_key([payload]), [])
            self.assertEqual(vault.service.get_by_key(name).key, name)
            self.assertEqual(len(vault.service.list()), 1)
            vault.update(name, "updated ' hint", 'updated-secret')
            self.assertEqual(vault._decrypt_passphrase(vault.service.get_by_key(name).password), 'updated-secret')
            vault.remove(name)
            self.assertEqual(vault.service.list(), [])

    def test_debug_logs_and_representations_do_not_contain_secrets(self):
        self.capture_logs(logging.DEBUG)
        (vault, _) = self.make_vault()
        with vault.open():
            add_entry(vault)
            entry = vault.service.get_by_key('entry')
            ciphertext = entry.password
            key = vault._entry_key.decode()
            self.assertNotIn(SECRET, repr(entry))
            self.assertNotIn(ciphertext, repr(entry))
            vault.update('entry', 'new hint', 'new-secret')
            with self.assertRaisesRegex(VaultSecurityException, 'database operation failed'):
                vault.service.repository.execute('INVALID SQL ' + SECRET)
        for sensitive in (MASTER, SECRET, ciphertext, key, 'new-secret'):
            self.assertNotIn(sensitive, self.log_output.getvalue())
        self.assertNotIn('INSERT INTO', self.log_output.getvalue())

    def test_configured_base64_password_is_rejected_and_not_logged(self):
        self.capture_logs(logging.DEBUG)
        encoded = base64.b64encode(MASTER.encode()).decode()
        (vault, path) = self.make_vault(configured_password=encoded)
        with self.assertRaisesRegex(VaultSecurityException, 'Remove hhs.vault.passphrase'):
            with vault.open():
                pass
        self.assertFalse(path.exists())
        self.assertNotIn(MASTER, self.log_output.getvalue())
        self.assertNotIn(encoded, self.log_output.getvalue())

    def test_changed_source_and_empty_vault_are_not_overwritten(self):
        (vault, path) = self.make_vault()
        path.touch()
        with self.assertRaisesRegex(VaultSecurityException, 'Empty vault'):
            with vault.open():
                pass
        self.assertEqual(path.read_bytes(), b'')
        path.unlink()
        with self.assertRaisesRegex(VaultSecurityException, 'changed outside'):
            with vault.open():
                path.write_bytes(b'external writer')
        self.assertEqual(path.read_bytes(), b'external writer')

    def test_group_writable_directory_is_rejected(self):
        (vault, path) = self.make_vault()
        path.parent.chmod(504)
        try:
            with self.assertRaisesRegex(VaultSecurityException, 'not writable by others'):
                with vault.open():
                    pass
        finally:
            path.parent.chmod(448)

    def test_password_retry_yields_once_and_invalid_token_in_body_is_not_retried(self):
        (vault, path) = self.make_vault()
        with vault.open():
            add_entry(vault)
        original = path.read_bytes()
        answers = iter(['wrong', MASTER])
        self.patch_target('vault.core.vault.getpass.getpass', lambda prompt: next(answers))
        with self.assertRaises(InvalidToken):
            with vault.open():
                self.assertTrue(vault.service.exists('entry'))
                raise InvalidToken
        self.assertEqual(path.read_bytes(), original)

    def test_partial_write_failure_cannot_replace_the_source(self):
        (vault, path) = self.make_vault()
        with vault.open():
            add_entry(vault)
        original = path.read_bytes()

        def fail_sync(fd):
            raise OSError('simulated full disk')
        with self.assertRaisesRegex(OSError, 'full disk'):
            with vault.open():
                self.patch_target('vault.core.vault_storage.os.fsync', fail_sync)
                add_entry(vault, 'new-entry')
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse(list(path.parent.glob('.vault-*.tmp')))

    def test_master_input_never_falls_back_to_echoing_stdin(self):
        import getpass
        (vault, path) = self.make_vault()

        def insecure_input(prompt):
            warnings.warn('Cannot disable echo', getpass.GetPassWarning)
            self.fail('Must stop before reading an echoed password')
        self.patch_target('vault.core.vault.getpass.getpass', insecure_input)
        with self.assertRaisesRegex(VaultSecurityException, 'hidden password'):
            with vault.open():
                pass
        self.assertFalse(path.exists())

    def test_hardlinked_vault_is_rejected(self):
        (vault, path) = self.make_vault()
        (original, _) = write_legacy(path)
        os.link(path, path.parent / 'linked-vault')
        with self.assertRaisesRegex(VaultSecurityException, 'without hard links'):
            with vault.open():
                pass
        self.assertEqual(path.read_bytes(), original)

    def test_failed_migration_backup_write_preserves_legacy_source(self):
        (vault, path) = self.make_vault()
        (original, _) = write_legacy(path)

        def fail_sync(fd):
            raise OSError('simulated backup write failure')
        with self.assertRaisesRegex(OSError, 'backup write failure'):
            with vault.open():
                self.patch_target('vault.core.vault_storage.os.fsync', fail_sync)
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse(Path(str(path) + '.legacy.bak').exists())

    def test_legacy_master_with_significant_whitespace_is_preserved(self):
        (vault, path) = self.make_vault()
        master = ' legacy-configured-password \t'
        write_legacy(path, master=master)
        self.patch_target('vault.core.vault.getpass.getpass', lambda prompt: master)
        with vault.open():
            self.assertEqual(vault._decrypt_passphrase(vault.service.get_by_key('key-0').password), SECRET)
        with vault.open():
            self.assertEqual(vault._decrypt_passphrase(vault.service.get_by_key('key-0').password), SECRET)

    def test_signal_during_backup_unwinds_before_closing_storage(self):
        from vault.__main__ import Main
        (vault, path) = self.make_vault()
        (original, _) = write_legacy(path)
        application = object.__new__(Main)
        application.vault = vault
        with self.assertRaises(SystemExit):
            with vault.open():
                self.patch_target('vault.core.vault_storage.os.fsync', lambda fd: application._abort(15, object()))
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse(Path(str(path) + '.legacy.bak').exists())
if __name__ == '__main__':
    unittest.main()
