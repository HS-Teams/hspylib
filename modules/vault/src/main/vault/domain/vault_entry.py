#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
   @project: HsPyLib-Vault
   @package: vault.domain
      @file: vault_entry.py
   @created: Tue, 4 May 2021
    @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
      @site: https://github.com/yorevs/hspylib
   @license: MIT - Please refer to <https://opensource.org/licenses/MIT>

   Copyright·(c)·2024,·HSPyLib
"""
from clitt.core.tui.minput.minput import MenuInput, minput
from collections import namedtuple
from datasource.crud_entity import CrudEntity
from datasource.identity import Identity
from hspylib.core.zoned_datetime import now
from textwrap import dedent
from typing import Optional, Union

import re


class VaultEntry(CrudEntity):
    """Represents the Vault domain object."""

    VaultId = namedtuple("VaultId", ["uuid"])

    # Vault entry format to be displayed when listing
    _DISPLAY_FORMAT = dedent(
        """
    [%BLUE%{}%NC%]:
            Name: %GREEN%{}%NC%
        Password: %GREEN%{}%NC%
            Hint: %GREEN%{}%NC%
        Modified: %GREEN%{}%NC%
    """
    )

    @staticmethod
    def prompt(existing_entry: Union["VaultEntry", None] = None) -> Optional["VaultEntry"]:
        """Create a vault entry from a form input."""

        entry = existing_entry or VaultEntry()
        # fmt: off
        form_fields = MenuInput.builder() \
            .field() \
                .label('Name') \
                .access_type('read-only') \
                .min_max_length(3, 50) \
                .value(entry.name) \
                .build() \
            .field() \
                .label('Hint') \
                .min_max_length(3, 50) \
                .value(entry.hint) \
                .build() \
            .field() \
                .label('Password') \
                .itype('password') \
                .min_max_length(4, 50) \
                .value(entry.password) \
                .build() \
            .build()
        # fmt: on

        if result := minput(form_fields, "Please fill the vault credential details"):
            entry.key = result.name
            entry.name = result.name
            entry.hint = result.hint
            entry.password = result.password
            entry.modified = now()

        return entry if result else None

    def __init__(
        self,
        entity_id: Identity = VaultId(Identity.auto().values),
        key: str = None,
        name: str = None,
        password: str = None,
        hint: str = None,
        modified: str = None,
    ):
        self.id = None  # Will be filled later
        super().__init__(entity_id)
        self.key = key
        self.name = name
        self.hint = hint
        self.password = password
        self.modified = modified or now()

    def __str__(self) -> str:
        return "VaultEntry(values redacted)"

    def __repr__(self) -> str:
        return str(self)

    def to_string(self, show_password: bool = False, show_hint: bool = False) -> str:
        """Return the string representation of this entry.
        :param show_password: whether to exhibit the password or not.
        :param show_hint: whether to exhibit the hint or not.
        """
        password = self.password if show_password else re.sub(".*", "*" * min(len(self.password), 5), self.password)
        hint = self.hint if show_hint else re.sub(".*", "*" * min(len(self.hint), 8), self.hint)
        return self._DISPLAY_FORMAT.format(self.key.upper(), self.name, password, hint, self.modified)
