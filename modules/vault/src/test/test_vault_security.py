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
import pytest
from cryptography.fernet import InvalidToken
from hspylib.modules.security.security import encode_file, encrypt_file
from vault.core.vault import Vault
from vault.core.vault_cipher import VaultCipher
from vault.exception.exceptions import VaultAuthenticationError, VaultSecurityException

MASTER = "synthetic master passphrase"
SECRET = "synthetic-entry-secret-'\"-\u00e7"
LEGACY_KEY = "e4f362fd1e02df6bc9c684c9310e3550"


@pytest.fixture
def factory(tmp_path, monkeypatch):
    for name in ("HHS_VAULT_FILE", "HHS_VAULT_USER", "HHS_VAULT_PASSPHRASE", "ACTIVE_PROFILE", "VAULT_HASHCODE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr("vault.core.vault.getpass.getpass", lambda prompt: MASTER)
    monkeypatch.setattr("vault.core.vault.sysout", lambda *args: None)
    counter = 0

    def make(name="secrets.vault", configured_password=""):
        nonlocal counter
        counter += 1
        resources = tmp_path / f"resources-{counter}"
        resources.mkdir()
        path = tmp_path / name
        (resources / "application.properties").write_text(
            f"hhs.vault.file={path}\nhhs.vault.user=alice\nhhs.vault.passphrase={configured_password}\n"
        )
        return Vault(str(resources)), path

    return make


def write_legacy(path, count=1, key=LEGACY_KEY, corrupt=False, master=MASTER):
    """Use the old public writer, independently of the new migration implementation."""
    database = path.with_suffix(".fixture.sqlite")
    conn = sqlite3.connect(database)
    conn.execute(
        "CREATE TABLE VAULT_ENTRIES (uuid TEXT PRIMARY KEY, key TEXT UNIQUE NOT NULL, "
        "name TEXT NOT NULL, password TEXT NOT NULL, hint TEXT NOT NULL, modified TEXT NOT NULL)"
    )
    encrypted = cryptocode.encrypt(SECRET, key)
    conn.executemany(
        "INSERT INTO VAULT_ENTRIES VALUES (?, ?, ?, ?, ?, ?)",
        [(str(i), f"key-{i}", f"name-{i}", "broken" if corrupt else encrypted, "hint", "2024-01-01")
         for i in range(count)],
    )
    conn.commit()
    conn.close()
    encoded = path.with_suffix(".fixture.encoded")
    encode_file(str(database), str(encoded), binary=True)
    encrypt_file(str(encoded), str(path), "alice:" + master)
    database.unlink()
    encoded.unlink()
    return path.read_bytes(), encrypted


def add_entry(vault, name="entry", secret=SECRET):
    vault.add(name, "synthetic hint", secret)


def test_new_vault_roundtrip_and_private_work_files(factory):
    vault, path = factory()
    old_umask = os.umask(0o022)
    try:
        with vault.open():
            add_entry(vault)
            work = Path(vault.service.repository.database)
            assert stat.S_IMODE(work.stat().st_mode) == 0o600
            assert stat.S_IMODE(work.parent.stat().st_mode) == 0o700
            assert SECRET.encode() not in work.read_bytes()
            assert not path.exists()
            assert not Path(str(path) + ".unlocked").exists()
    finally:
        os.umask(old_umask)
    assert not work.parent.exists()
    assert path.read_bytes().startswith(VaultCipher.MAGIC)
    assert SECRET.encode() not in path.read_bytes()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(Path(str(path) + ".lock").stat().st_mode) == 0o600
    reopened, _ = factory()
    with reopened.open():
        entry = reopened.service.get_by_key("entry")
        assert reopened._decrypt_passphrase(entry.password) == SECRET
        assert cryptocode.decrypt(entry.password, LEGACY_KEY) is False


def test_keys_and_salts_are_independent_between_vaults(factory):
    first, _ = factory("first.vault")
    second, _ = factory("second.vault")
    with first.open(), second.open():
        add_entry(first)
        add_entry(second)
        assert first._entry_key != second._entry_key
        assert first._cipher.salt != second._cipher.salt
        with pytest.raises(InvalidToken):
            second._decrypt_passphrase(first.service.get_by_key("entry").password)


def test_migration_preserves_every_entry_and_original_backup(factory):
    vault, path = factory()
    original, old_ciphertext = write_legacy(path, count=502)
    with vault.open():
        entries = vault.service.list()
        assert len(entries) == 502
        assert path.read_bytes() == original
        for entry in entries:
            assert vault._decrypt_passphrase(entry.password) == SECRET
            assert entry.modified == "2024-01-01"
        assert old_ciphertext.encode() not in vault.service.repository.snapshot()
    backup = Path(str(path) + ".legacy.bak")
    assert backup.read_bytes() == original
    assert stat.S_IMODE(backup.stat().st_mode) == 0o600
    reopened, _ = factory()
    with reopened.open():
        assert len(reopened.service.list()) == 502
    assert backup.read_bytes() == original


def test_custom_legacy_key_is_supported_only_for_migration(factory, monkeypatch):
    vault, path = factory()
    original, _ = write_legacy(path, key="custom legacy key")
    with pytest.raises(VaultSecurityException, match="Legacy entry decryption failed"):
        with vault.open():
            pytest.fail("Wrong legacy key must not open")
    assert path.read_bytes() == original
    monkeypatch.setenv("VAULT_HASHCODE", "custom legacy key")
    with vault.open():
        assert vault._decrypt_passphrase(vault.service.get_by_key("key-0").password) == SECRET
    monkeypatch.setenv("VAULT_HASHCODE", "different and irrelevant now")
    with vault.open():
        assert vault._decrypt_passphrase(vault.service.get_by_key("key-0").password) == SECRET


@pytest.mark.parametrize("legacy", [False, True])
def test_wrong_master_password_preserves_original(factory, monkeypatch, legacy):
    vault, path = factory()
    if legacy:
        write_legacy(path)
    else:
        with vault.open():
            add_entry(vault)
    original = path.read_bytes()
    monkeypatch.setattr("vault.core.vault.getpass.getpass", lambda prompt: "wrong password")
    with pytest.raises(VaultAuthenticationError):
        with vault.open():
            pytest.fail("Wrong master password must not open")
    assert path.read_bytes() == original
    assert vault._storage is None
    assert vault._entry_key is None
    assert not Path(str(path) + ".legacy.bak").exists()


@pytest.mark.parametrize("offset", [0, len(VaultCipher.MAGIC), -10])
def test_tampered_vault_never_replaced(factory, offset):
    vault, path = factory()
    with vault.open():
        add_entry(vault)
    damaged = bytearray(path.read_bytes())
    damaged[offset] ^= 1
    path.write_bytes(damaged)
    with pytest.raises(VaultAuthenticationError):
        with vault.open():
            pytest.fail("Damaged vault must not open")
    assert path.read_bytes() == damaged


def test_invalid_legacy_entry_aborts_without_backup_or_overwrite(factory):
    vault, path = factory()
    original, _ = write_legacy(path, corrupt=True)
    with pytest.raises(VaultSecurityException):
        with vault.open():
            pytest.fail("Invalid legacy entry must not migrate")
    assert path.read_bytes() == original
    assert not Path(str(path) + ".legacy.bak").exists()


@pytest.mark.parametrize("failure", [RuntimeError, KeyboardInterrupt, SystemExit])
def test_interrupted_operation_discards_changes_and_cleans_up(factory, failure):
    vault, path = factory()
    with vault.open():
        add_entry(vault)
    original = path.read_bytes()
    with pytest.raises(failure):
        with vault.open():
            work = Path(vault.service.repository.database)
            add_entry(vault, "discard-me")
            raise failure()
    assert path.read_bytes() == original
    assert not work.parent.exists()
    with pytest.raises(VaultSecurityException, match="locked"):
        vault.service.list()


def test_failed_atomic_replace_preserves_original_and_verified_backup(factory, monkeypatch):
    vault, path = factory()
    original, _ = write_legacy(path)

    def fail_replace(*args, **kwargs):
        raise OSError("simulated disk failure")

    monkeypatch.setattr("vault.core.vault_storage.os.replace", fail_replace)
    with pytest.raises(OSError, match="simulated"):
        with vault.open():
            work = Path(vault.service.repository.database)
    assert path.read_bytes() == original
    assert Path(str(path) + ".legacy.bak").read_bytes() == original
    assert not work.parent.exists()
    assert not list(path.parent.glob(".vault-*.tmp"))


@pytest.mark.parametrize("suffix", ["", ".lock", ".legacy.bak"])
def test_symlink_targets_are_never_read_or_overwritten(factory, suffix):
    vault, path = factory()
    target = path.parent / "unrelated"
    target.write_bytes(b"unrelated contents")
    if suffix == ".legacy.bak":
        write_legacy(path)
    Path(str(path) + suffix).symlink_to(target)
    with pytest.raises((OSError, VaultSecurityException)):
        with vault.open():
            pass
    assert target.read_bytes() == b"unrelated contents"


def test_legacy_residue_and_conflicting_backups_are_preserved(factory):
    vault, path = factory()
    original, _ = write_legacy(path)
    residue = Path(str(path) + ".unlocked")
    residue.write_bytes(b"recover me")
    with pytest.raises(VaultSecurityException, match="manual recovery"):
        with vault.open():
            pass
    assert residue.read_bytes() == b"recover me"
    residue.unlink()
    backup = Path(str(path) + ".legacy.bak")
    backup.write_bytes(b"other backup")
    with pytest.raises(VaultSecurityException, match="different contents"):
        with vault.open():
            pass
    assert backup.read_bytes() == b"other backup"
    assert path.read_bytes() == original


def test_second_process_cannot_open_locked_vault(factory):
    vault, path = factory()
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path))
    code = (
        "import sys; from vault.core.vault_storage import VaultStorage; "
        "s=VaultStorage(sys.argv[1]); s.acquire()"
    )
    with vault.open():
        result = subprocess.run([sys.executable, "-c", code, str(path)], env=env, capture_output=True, text=True)
        assert result.returncode != 0
        assert "already open" in result.stderr


def test_sql_injection_and_quoted_values_are_data(factory):
    vault, _ = factory()
    name = "entry'\"; DROP TABLE VAULT_ENTRIES;--"
    with vault.open():
        add_entry(vault, name)
        payload = "' UNION SELECT uuid,password,name,password,hint,modified FROM VAULT_ENTRIES -- "
        assert vault.service.list_by_key([payload]) == []
        assert vault.service.get_by_key(name).key == name
        assert len(vault.service.list()) == 1
        vault.update(name, "updated ' hint", "updated-secret")
        assert vault._decrypt_passphrase(vault.service.get_by_key(name).password) == "updated-secret"
        vault.remove(name)
        assert vault.service.list() == []


def test_debug_logs_and_representations_do_not_contain_secrets(factory, caplog):
    caplog.set_level(logging.DEBUG)
    vault, _ = factory()
    with vault.open():
        add_entry(vault)
        entry = vault.service.get_by_key("entry")
        ciphertext = entry.password
        key = vault._entry_key.decode()
        assert SECRET not in repr(entry)
        assert ciphertext not in repr(entry)
        vault.update("entry", "new hint", "new-secret")
        with pytest.raises(VaultSecurityException, match="database operation failed"):
            vault.service.repository.execute("INVALID SQL " + SECRET)
    for sensitive in (MASTER, SECRET, ciphertext, key, "new-secret"):
        assert sensitive not in caplog.text
    assert "INSERT INTO" not in caplog.text


def test_configured_base64_password_is_rejected_and_not_logged(factory, caplog):
    caplog.set_level(logging.DEBUG)
    encoded = base64.b64encode(MASTER.encode()).decode()
    vault, path = factory(configured_password=encoded)
    with pytest.raises(VaultSecurityException, match="Remove hhs.vault.passphrase"):
        with vault.open():
            pass
    assert not path.exists()
    assert MASTER not in caplog.text
    assert encoded not in caplog.text


def test_changed_source_and_empty_vault_are_not_overwritten(factory):
    vault, path = factory()
    path.touch()
    with pytest.raises(VaultSecurityException, match="Empty vault"):
        with vault.open():
            pass
    assert path.read_bytes() == b""
    path.unlink()
    with pytest.raises(VaultSecurityException, match="changed outside"):
        with vault.open():
            path.write_bytes(b"external writer")
    assert path.read_bytes() == b"external writer"


def test_group_writable_directory_is_rejected(factory):
    vault, path = factory()
    path.parent.chmod(0o770)
    try:
        with pytest.raises(VaultSecurityException, match="not writable by others"):
            with vault.open():
                pass
    finally:
        path.parent.chmod(0o700)


def test_password_retry_yields_once_and_invalid_token_in_body_is_not_retried(factory, monkeypatch):
    vault, path = factory()
    with vault.open():
        add_entry(vault)
    original = path.read_bytes()
    answers = iter(["wrong", MASTER])
    monkeypatch.setattr("vault.core.vault.getpass.getpass", lambda prompt: next(answers))
    with pytest.raises(InvalidToken):
        with vault.open():
            assert vault.service.exists("entry")
            raise InvalidToken
    assert path.read_bytes() == original


def test_partial_write_failure_cannot_replace_the_source(factory, monkeypatch):
    vault, path = factory()
    with vault.open():
        add_entry(vault)
    original = path.read_bytes()

    def fail_sync(fd):
        raise OSError("simulated full disk")

    with pytest.raises(OSError, match="full disk"):
        with vault.open():
            monkeypatch.setattr("vault.core.vault_storage.os.fsync", fail_sync)
            add_entry(vault, "new-entry")
    assert path.read_bytes() == original
    assert not list(path.parent.glob(".vault-*.tmp"))


def test_master_input_never_falls_back_to_echoing_stdin(factory, monkeypatch):
    import getpass

    vault, path = factory()

    def insecure_input(prompt):
        warnings.warn("Cannot disable echo", getpass.GetPassWarning)
        pytest.fail("Must stop before reading an echoed password")

    monkeypatch.setattr("vault.core.vault.getpass.getpass", insecure_input)
    with pytest.raises(VaultSecurityException, match="hidden password"):
        with vault.open():
            pass
    assert not path.exists()


def test_hardlinked_vault_is_rejected(factory):
    vault, path = factory()
    original, _ = write_legacy(path)
    os.link(path, path.parent / "linked-vault")
    with pytest.raises(VaultSecurityException, match="without hard links"):
        with vault.open():
            pass
    assert path.read_bytes() == original


def test_failed_migration_backup_write_preserves_legacy_source(factory, monkeypatch):
    vault, path = factory()
    original, _ = write_legacy(path)

    def fail_sync(fd):
        raise OSError("simulated backup write failure")

    with pytest.raises(OSError, match="backup write failure"):
        with vault.open():
            monkeypatch.setattr("vault.core.vault_storage.os.fsync", fail_sync)
    assert path.read_bytes() == original
    assert not Path(str(path) + ".legacy.bak").exists()


def test_legacy_master_with_significant_whitespace_is_preserved(factory, monkeypatch):
    vault, path = factory()
    master = " legacy-configured-password \t"
    write_legacy(path, master=master)
    monkeypatch.setattr("vault.core.vault.getpass.getpass", lambda prompt: master)
    with vault.open():
        assert vault._decrypt_passphrase(vault.service.get_by_key("key-0").password) == SECRET
    with vault.open():
        assert vault._decrypt_passphrase(vault.service.get_by_key("key-0").password) == SECRET


def test_signal_during_backup_unwinds_before_closing_storage(factory, monkeypatch):
    from vault.__main__ import Main

    vault, path = factory()
    original, _ = write_legacy(path)
    application = object.__new__(Main)
    application.vault = vault
    with pytest.raises(SystemExit):
        with vault.open():
            monkeypatch.setattr("vault.core.vault_storage.os.fsync", lambda fd: application._abort(15, object()))
    assert path.read_bytes() == original
    assert not Path(str(path) + ".legacy.bak").exists()
