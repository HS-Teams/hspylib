"""Private work files, exclusive access and atomic encrypted persistence (POSIX)."""

import fcntl
import os
import stat
import tempfile
import uuid
from pathlib import Path

from vault.exception.exceptions import VaultSecurityException


class VaultStorage:
    MAX_FILE_SIZE = 64 * 1024 * 1024

    def __init__(self, filename: str):
        self.path = Path(filename).expanduser().absolute()
        self._directory = None
        self._lock = None
        self._workspace = None
        self.original = None
        self.database = None

    def acquire(self) -> None:
        try:
            self._directory = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            info = os.fstat(self._directory)
            if info.st_uid != os.getuid() or info.st_mode & 0o022:
                raise VaultSecurityException("Vault directory must be owned by you and not writable by others")
            self._lock = self._open(self.path.name + ".lock", os.O_RDWR | os.O_CREAT)
            os.fchmod(self._lock, 0o600)
            try:
                fcntl.flock(self._lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise VaultSecurityException("Vault is already open in another process") from None
            for suffix in (".unlocked", ".unlocked-encoded"):
                if self._exists(self.path.name + suffix):
                    raise VaultSecurityException(
                        "Legacy unlocked files need manual recovery; no files were changed"
                    )
            self.original = self._read(self.path.name)
            if self.original == b"":
                raise VaultSecurityException("Empty vault file; restore a verified backup before opening")
        except BaseException:
            self.close()
            raise

    def prepare_database(self, data: bytes | None) -> str:
        self._workspace = tempfile.TemporaryDirectory(prefix="hspylib-vault-")
        os.chmod(self._workspace.name, 0o700)
        self.database = str(Path(self._workspace.name) / "database.sqlite")
        fd = os.open(self.database, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as stream:
            if data is not None:
                stream.write(data)
        return self.database

    def save(self, encrypted: bytes, migrating: bool = False) -> None:
        if len(encrypted) > self.MAX_FILE_SIZE:
            raise VaultSecurityException("Vault exceeds the supported file size")
        if self._read(self.path.name) != self.original:
            raise VaultSecurityException("Vault changed outside this session; refusing to overwrite it")
        if migrating:
            self._backup_legacy()
        temporary = ".vault-" + uuid.uuid4().hex + ".tmp"
        try:
            self._write_new(temporary, encrypted)
            if self._read(temporary) != encrypted:
                raise VaultSecurityException("Encrypted vault verification failed before replacement")
            os.replace(temporary, self.path.name, src_dir_fd=self._directory, dst_dir_fd=self._directory)
            os.fsync(self._directory)
            self.original = encrypted
        finally:
            if self._exists(temporary):
                os.unlink(temporary, dir_fd=self._directory)

    def close(self) -> None:
        try:
            if self._workspace is not None:
                self._workspace.cleanup()
        finally:
            self._workspace = None
            self.database = None
            if self._lock is not None:
                os.close(self._lock)
                self._lock = None
            if self._directory is not None:
                os.close(self._directory)
                self._directory = None
            self.original = None

    def _backup_legacy(self) -> None:
        name = self.path.name + ".legacy.bak"
        backup = self._read(name)
        if backup is not None:
            if backup != self.original:
                raise VaultSecurityException("Migration backup already exists with different contents")
            fd = self._open(name, os.O_RDONLY)
            try:
                os.fchmod(fd, 0o600)
            finally:
                os.close(fd)
            return
        self._write_new(name, self.original)
        os.fsync(self._directory)

    def _open(self, name: str, flags: int) -> int:
        fd = os.open(name, flags | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=self._directory)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
            os.close(fd)
            raise VaultSecurityException("Vault files must be regular, owned files without hard links")
        return fd

    def _read(self, name: str) -> bytes | None:
        try:
            fd = self._open(name, os.O_RDONLY)
        except FileNotFoundError:
            return None
        with os.fdopen(fd, "rb") as stream:
            data = stream.read(self.MAX_FILE_SIZE + 1)
        if len(data) > self.MAX_FILE_SIZE:
            raise VaultSecurityException("Vault exceeds the supported file size")
        return data

    def _write_new(self, name: str, data: bytes) -> None:
        fd = self._open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            os.unlink(name, dir_fd=self._directory)
            raise

    def _exists(self, name: str) -> bool:
        try:
            os.stat(name, dir_fd=self._directory, follow_symlinks=False)
            return True
        except FileNotFoundError:
            return False
