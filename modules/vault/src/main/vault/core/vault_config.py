#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
   @project: HsPyLib-Vault
   @package: vault.core
      @file: vault_config.py
   @created: Tue, 4 May 2021
    @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
      @site: https://github.com/yorevs/hspylib
   @license: MIT - Please refer to <https://opensource.org/licenses/MIT>

   Copyright·(c)·2024,·HSPyLib
"""
from datasource.db_configuration import DBConfiguration


class VaultConfig(DBConfiguration):
    """Holds the vault configurations."""

    INSTANCE: 'VaultConfig' = None

    def __init__(self, resource_dir: str):
        super().__init__(resource_dir)
        self._vault_user = self["hhs.vault.user"]
        self._passphrase = self["hhs.vault.passphrase"]
        self._vault_file = self["hhs.vault.file"]
        VaultConfig.INSTANCE = self if VaultConfig.INSTANCE is None else VaultConfig.INSTANCE

    def __str__(self) -> str:
        return "VaultConfig(values redacted)"

    @property
    def vault_user(self) -> str:
        """Return the vault user"""
        return self._vault_user

    @property
    def passphrase(self) -> str:
        """Return the vault user passphrase"""
        return self._passphrase

    @property
    def database(self) -> str:
        raise RuntimeError("Vault database is available only within an authenticated session")

    @property
    def vault_file(self) -> str:
        """Return the locked vault database filename"""
        return self._vault_file

    @property
    def unlocked_vault_file(self) -> str:
        """Return the locked vault database filename"""
        return f"{self._vault_file}.unlocked"
