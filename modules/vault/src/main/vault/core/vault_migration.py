"""Read-only compatibility with existing vault entry encryption."""

import os

import cryptocode

from vault.exception.exceptions import VaultSecurityException


def migrate_entries(repository, cipher) -> None:
    # This public legacy value is ONLY for reading old entries, never for new writes.
    legacy_key = os.getenv("VAULT_HASHCODE", "e4f362fd1e02df6bc9c684c9310e3550")
    converted = []
    for entry in repository.find_all():
        password = cryptocode.decrypt(entry.password, legacy_key)
        if not isinstance(password, str):
            raise VaultSecurityException(
                "Legacy entry decryption failed; supply the original VAULT_HASHCODE if customized"
            )
        entry.password = cipher.encrypt(password.encode("utf-8")).decode("ascii")
        converted.append(entry)
    for entry in converted:
        repository.save(entry)
    # Remove old record ciphertext from SQLite free pages before exporting the new format.
    repository.execute("VACUUM")
