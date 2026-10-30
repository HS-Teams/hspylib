"""Versioned, authenticated vault encryption. Legacy keys are read-only."""

import base64
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class VaultCipher:
    MAGIC = b"HSPYVAULT\x02"
    SALT_SIZE = 16
    KEY_SIZE = 44
    MEMORY_KIB = 64 * 1024
    ITERATIONS = 3
    LANES = 4

    def __init__(self, passphrase: str, salt: bytes):
        self.salt = salt
        key = Argon2id(
            salt=salt, length=32, iterations=self.ITERATIONS,
            lanes=self.LANES, memory_cost=self.MEMORY_KIB,
        ).derive(passphrase.encode("utf-8"))
        self._fernet = Fernet(base64.urlsafe_b64encode(key))

    @classmethod
    def create(cls, passphrase: str) -> "VaultCipher":
        return cls(passphrase, os.urandom(cls.SALT_SIZE))

    @classmethod
    def open(cls, data: bytes, passphrase: str) -> tuple["VaultCipher", bytes, bytes]:
        offset = len(cls.MAGIC) + cls.SALT_SIZE
        if not data.startswith(cls.MAGIC) or len(data) <= offset:
            raise InvalidToken
        cipher = cls(passphrase, data[len(cls.MAGIC):offset])
        payload = cipher._fernet.decrypt(data[offset:])
        entry_key, database = payload[:cls.KEY_SIZE], payload[cls.KEY_SIZE:]
        try:
            Fernet(entry_key)
        except (ValueError, TypeError):
            raise InvalidToken from None
        if not database.startswith(b"SQLite format 3\x00"):
            raise InvalidToken
        return cipher, entry_key, database

    def seal(self, entry_key: bytes, database: bytes) -> bytes:
        payload = entry_key + database
        token = self._fernet.encrypt(payload)
        if self._fernet.decrypt(token) != payload:
            raise InvalidToken
        return self.MAGIC + self.salt + token


def decrypt_legacy(data: bytes, passphrase: str) -> bytes:
    """Read the original PBKDF2/Fernet + Base64 format; never write it."""
    key = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32, salt=b"HsPyLib", iterations=100000,
    ).derive(passphrase.encode("utf-8"))
    encoded = Fernet(base64.urlsafe_b64encode(key)).decrypt(data)
    return base64.b64decode(encoded, validate=True)
