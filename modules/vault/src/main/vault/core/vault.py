#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
   @project: HsPyLib-Vault
   @package: vault.core
      @file: vault.py
   @created: Tue, 4 May 2021
    @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
      @site: https://github.com/yorevs/hspylib
   @license: MIT - Please refer to <https://opensource.org/licenses/MIT>

   Copyright·(c)·2024,·HSPyLib
"""
import binascii
import contextlib
import getpass
import logging as log
import uuid
import warnings

import pyperclip
from cryptography.fernet import Fernet, InvalidToken
from datasource.identity import Identity
from hspylib.core.preconditions import check_not_none
from hspylib.core.tools.commons import syserr, sysout
from vault.core.vault_cipher import VaultCipher, decrypt_legacy
from vault.core.vault_config import VaultConfig
from vault.core.vault_service import VaultService
from vault.core.vault_storage import VaultStorage
from vault.domain.vault_entry import VaultEntry
from vault.exception.exceptions import VaultAuthenticationError, VaultSecurityException
from typing import List


class Vault:
    """Authenticated vault sessions with atomic persistence and private work files."""

    MAX_AUTH_RETRIES = 3
    MIN_NEW_PASSPHRASE_LENGTH = 12

    def __init__(self, resource_dir: str) -> None:
        self._configs = VaultConfig(resource_dir)
        self.service = VaultService(self._configs)
        self._storage = None
        self._cipher = None
        self._entry_key = None
        self._entries_cipher = None
        self._is_unlocked = False
        self._migrating = False

    def __str__(self):
        return "Vault(unlocked)" if self._is_unlocked else "Vault(locked)"

    @property
    def configs(self) -> VaultConfig:
        return self._configs

    @contextlib.contextmanager
    def open(self):
        if self._storage is not None:
            raise VaultSecurityException("Vault session is already active")
        if self._configs.passphrase:
            raise VaultSecurityException(
                "Remove hhs.vault.passphrase from configuration; enter the master passphrase at the prompt"
            )
        if not self._configs.vault_file:
            raise VaultSecurityException("Configure hhs.vault.file before opening the vault")
        self._storage = VaultStorage(self._configs.vault_file)
        try:
            self._storage.acquire()
            for _ in range(self.MAX_AUTH_RETRIES):
                passphrase = self._read_passphrase(self._storage.original is None)
                try:
                    self._unlock_vault(passphrase)
                    break
                except (InvalidToken, UnicodeDecodeError, binascii.Error):
                    syserr("Authentication failed or vault is damaged")
                finally:
                    passphrase = None
            else:
                raise VaultAuthenticationError("Unable to authenticate vault")
            yield True
            self.close()
        finally:
            self.discard()

    def close(self) -> bool:
        """Commit only a successfully completed operation. Always release resources."""
        try:
            if self._is_unlocked:
                database = self.service.repository.snapshot()
                encrypted = self._cipher.seal(self._entry_key, database)
                self._storage.save(encrypted, migrating=self._migrating)
                if self._migrating:
                    log.info("Vault migration completed; encrypted legacy backup preserved")
        finally:
            self.discard()
        return True

    def discard(self) -> None:
        """Discard an incomplete operation without replacing the last valid vault."""
        self._is_unlocked = False
        self._cipher = self._entries_cipher = self._entry_key = None
        self._migrating = False
        self.service.repository.bind(None)
        if self._storage is not None:
            storage, self._storage = self._storage, None
            storage.close()

    def list(self, filter_expr: List[str] = None) -> None:
        """List all vault entries filtered by filter_expr
        :param filter_expr: The entry filter expression.
        """
        self._require_unlocked()
        data = self.service.list_by_key(filter_expr)
        if len(data) > 0:
            sysout(
                "%YELLOW%{} {}%NC%".format(
                    f"\n-=- Listing all ({len(data)}) vault entries ",
                    f"matching '{filter_expr}' -=-" if filter_expr else "-=-",
                )
            )
            for entry in data:
                sysout(entry.to_string())
        else:
            if filter_expr:
                sysout(f"%YELLOW%%EOL%-=- No results to display containing '{filter_expr}' -=-%EOL%%NC%")
            else:
                sysout("%YELLOW%%EOL%-=- Vault is empty -=-%EOL%%NC%")
        log.debug("Vault list issued. User=%s", getpass.getuser())

    def add(self, key: str, hint: str | None, password: str | None) -> None:
        """Add a vault entry
        :param key: the vault entry key to be added.
        :param hint: the vault entry hint to be added.
        :param password: the vault entry password to be added.
        """
        self._require_unlocked()
        check_not_none(key)
        if not self.service.exists(key):
            entry = VaultEntry(Identity(VaultEntry.VaultId(uuid.uuid4().hex)), key, key, password, hint)
            if not hint or not password:
                entry = VaultEntry.prompt(entry)
            if entry:
                entry.password = self._encrypt_passphrase(entry.password)
                self.service.save(entry)
                sysout(f"%GREEN%%EOL%=== Entry saved ===%EOL%%EOL%%NC%{entry.to_string()}")
        else:
            log.error("Attempt to add to Vault failed for key=%s", key)
            syserr(f"### Entry specified by '{key}' already exists in vault")
        log.debug("Vault add issued. User=%s", getpass.getuser())

    def update(self, key: str, hint: str | None, password: str | None) -> None:
        """Update a vault entry
        :param key: the vault entry key to be updated.
        :param hint: the vault entry hint to be updated.
        :param password: the vault entry password to be updated.
        """
        self._require_unlocked()
        check_not_none(key)
        if entry := self.service.get_by_key(key):
            entry.hint = hint if hint else entry.hint
            entry.password = password if password else self._decrypt_passphrase(entry.password)
            if not hint or not password:
                entry = VaultEntry.prompt(entry)
            if entry:
                entry.password = self._encrypt_passphrase(entry.password)
                self.service.save(entry)
                sysout(f"%GREEN%%EOL%=== Entry updated ===%EOL%%EOL%%NC%{entry.to_string()}")
        else:
            log.error("Attempt to update Vault failed for key=%s", key)
            syserr(f"### No entry specified by '{key}' was found in vault")
        log.debug("Vault update issued. User=%s", getpass.getuser())

    def get(self, key, show: bool = False) -> None:
        """Display the vault entry specified by name
        :param key: the vault entry key to get
        :param show: whether to display the vault entry or copy to clipboard.
        """
        self._require_unlocked()
        entry = self.service.get_by_key(key)
        if entry:
            entry.password = self._decrypt_passphrase(entry.password)
            if show:
                sysout(f"\n{entry.to_string(True, True)}")
            else:
                sysout("%GREEN%Password copied to the clipboard!%NC%")
                pyperclip.copy(entry.password)
        else:
            log.error("Attempt to get from Vault failed for key=%s", key)
            syserr(f"### No entry specified by '{key}' was found in vault ###")
        log.debug("Vault get issued. User=%s", getpass.getuser())

    def remove(self, key: str) -> None:
        """Remove a vault entry
        :param key: The vault entry key to be removed
        """
        self._require_unlocked()
        entry = self.service.get_by_key(key)
        if entry:
            self.service.remove(entry)
            sysout(f"%GREEN%%EOL%=== Entry removed ===%EOL%%EOL%%NC%{entry.to_string()}")
        else:
            log.error("Attempt to remove to Vault failed for key=%s", key)
            syserr(f"### No entry specified by '{key}' was found in vault")
        log.debug("Vault remove issued. User=%s", getpass.getuser())

    def _encrypt_passphrase(self, passphrase: str) -> str:
        self._require_unlocked()
        return self._entries_cipher.encrypt(passphrase.encode("utf-8")).decode("ascii")

    def _decrypt_passphrase(self, passphrase: str) -> str:
        self._require_unlocked()
        return self._entries_cipher.decrypt(passphrase.encode("ascii")).decode("utf-8")

    def _read_passphrase(self, creating: bool) -> str:
        while True:
            passphrase = self._hidden_input("Enter passphrase:")
            if not creating:
                break
            if len(passphrase) < self.MIN_NEW_PASSPHRASE_LENGTH:
                syserr("Use at least 12 characters for a new master passphrase")
                continue
            if passphrase == self._hidden_input("Repeat passphrase:"):
                break
            syserr("Passphrase and confirmation mismatch")
        return f"{self._configs.vault_user}:{passphrase}"

    @staticmethod
    def _hidden_input(prompt: str) -> str:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            try:
                return getpass.getpass(prompt)
            except getpass.GetPassWarning:
                raise VaultSecurityException("A terminal with hidden password input is required") from None

    def _unlock_vault(self, passphrase: str) -> None:
        original = self._storage.original
        self._migrating = original is not None and not original.startswith(VaultCipher.MAGIC)
        if original is None:
            self._cipher = VaultCipher.create(passphrase)
            self._entry_key = Fernet.generate_key()
            database = None
        elif self._migrating:
            database = decrypt_legacy(original, passphrase)
            self._cipher = VaultCipher.create(passphrase)
            self._entry_key = Fernet.generate_key()
        else:
            self._cipher, self._entry_key, database = VaultCipher.open(original, passphrase)
        self._entries_cipher = Fernet(self._entry_key)
        self.service.repository.bind(self._storage.prepare_database(database))
        if original is None:
            self.service.create_vault_db()
        self.service.repository.validate()
        if self._migrating:
            from vault.core.vault_migration import migrate_entries
            migrate_entries(self.service.repository, self._entries_cipher)
        else:
            for entry in self.service.list():
                try:
                    self._entries_cipher.decrypt(entry.password.encode("ascii")).decode("utf-8")
                except (InvalidToken, UnicodeError):
                    raise VaultSecurityException("Invalid encrypted vault entry") from None
        self._is_unlocked = True

    def _require_unlocked(self) -> None:
        if not self._is_unlocked:
            raise VaultSecurityException("Vault is locked")
