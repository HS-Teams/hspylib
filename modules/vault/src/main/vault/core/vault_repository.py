#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
   @project: HsPyLib-Vault
   @package: vault.core
      @file: vault_repository.py
   @created: Tue, 4 May 2021
    @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
      @site: https://github.com/yorevs/hspylib
   @license: MIT - Please refer to <https://opensource.org/licenses/MIT>

   Copyright·(c)·2024,·HSPyLib
"""
import contextlib
import sqlite3
from pathlib import Path
from typing import Optional

from datasource.identity import Identity
from vault.domain.vault_entry import VaultEntry
from vault.exception.exceptions import VaultSecurityException


class VaultRepository:
    """Session-bound SQLite access: private database, bound values, no SQL logging."""

    COLUMNS = ("uuid", "key", "name", "password", "hint", "modified")

    def __init__(self, vault_config):
        self._database = None

    def bind(self, database: str | None) -> None:
        self._database = database

    @property
    def database(self) -> str:
        if self._database is None:
            raise VaultSecurityException("Vault is locked")
        return self._database

    def execute(self, sql_statement: str, **kwargs):
        try:
            with contextlib.closing(sqlite3.connect(self.database)) as conn:
                conn.execute("PRAGMA trusted_schema=OFF")
                conn.execute("PRAGMA secure_delete=ON")
                conn.execute("PRAGMA temp_store=MEMORY")
                conn.execute("PRAGMA journal_mode=MEMORY")
                with conn:
                    cursor = conn.execute(sql_statement, tuple(kwargs.values()))
                    return cursor.rowcount, cursor.fetchall()
        except sqlite3.Error:
            raise VaultSecurityException("Vault database operation failed") from None

    def validate(self) -> None:
        schema = self.execute("SELECT type, name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")[1]
        if schema != [("table", "VAULT_ENTRIES")]:
            raise VaultSecurityException("Unexpected vault database schema")
        columns = self.execute("PRAGMA table_info(VAULT_ENTRIES)")[1]
        if tuple(row[1] for row in columns) != self.COLUMNS:
            raise VaultSecurityException("Unexpected vault database columns")
        if self.execute("PRAGMA quick_check")[1] != [("ok",)]:
            raise VaultSecurityException("Vault database integrity check failed")
        rows = self.execute("SELECT uuid, key, name, password, hint, modified FROM VAULT_ENTRIES")[1]
        if any(not all(isinstance(value, str) for value in row) for row in rows):
            raise VaultSecurityException("Invalid vault entry")
        if len({row[0] for row in rows}) != len(rows) or len({row[1] for row in rows}) != len(rows):
            raise VaultSecurityException("Duplicate vault entries")

    def snapshot(self) -> bytes:
        self.validate()
        return Path(self.database).read_bytes()

    def find_by_key(self, key: str) -> Optional[VaultEntry]:
        rows = self.execute("SELECT * FROM VAULT_ENTRIES WHERE key = ?", key=key)[1]
        return self.to_entity_type(rows[0]) if rows else None

    def exists(self, key: str) -> bool:
        return bool(self.execute("SELECT 1 FROM VAULT_ENTRIES WHERE key = ?", key=key)[1])

    def find_all(self, filters=None):
        filters = filters or []
        clauses = " OR ".join("key LIKE ?" for _ in filters)
        sql = "SELECT * FROM VAULT_ENTRIES"
        if clauses:
            sql += " WHERE " + clauses
        sql += " ORDER BY key, modified"
        args = {str(i): f"%{value}%" for i, value in enumerate(filters)}
        return [self.to_entity_type(row) for row in self.execute(sql, **args)[1]]

    def save(self, entity: VaultEntry) -> None:
        self.execute(
            "INSERT INTO VAULT_ENTRIES (uuid, key, name, password, hint, modified) VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(uuid) DO UPDATE SET key=excluded.key, name=excluded.name, "
            "password=excluded.password, hint=excluded.hint, modified=excluded.modified",
            uuid=entity.identity.values[0], key=entity.key, name=entity.name,
            password=entity.password, hint=entity.hint, modified=entity.modified,
        )

    def delete(self, entity: VaultEntry) -> None:
        self.execute("DELETE FROM VAULT_ENTRIES WHERE uuid = ?", uuid=entity.identity.values[0])

    def to_entity_type(self, row: tuple) -> VaultEntry:
        return VaultEntry(Identity(VaultEntry.VaultId(row[0])), *row[1:])
