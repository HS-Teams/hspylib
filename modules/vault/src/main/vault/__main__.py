#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
   @project: HsPyLib-Vault
   @package: vault
      @file: __main__.py
   @created: Tue, 4 May 2021
    @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
      @site: https://github.com/yorevs/hspylib
   @license: MIT - Please refer to <https://opensource.org/licenses/MIT>

   Copyright·(c)·2024,·HSPyLib
"""

from clitt.core.tui.tui_application import TUIApplication
from hspylib.core.enums.charset import Charset
from hspylib.core.tools.commons import hook_exit_signals, syserr, to_bool
from hspylib.core.zoned_datetime import now
from hspylib.modules.application.exit_status import ExitStatus
from hspylib.modules.application.version import Version
from textwrap import dedent
from vault.__classpath__ import classpath
from vault.core.vault import Vault
from vault.core.vault_argument_parser import VaultArgumentParser
from vault.core.vault_config import VaultConfig
from vault.exception.exceptions import VaultOpenError

import logging as log
import sys


class Main(TUIApplication):
    """HsPyLib Vault - Manage your secrets"""

    CONFIG_CLASS = VaultConfig
    PARSER_CLASS = VaultArgumentParser

    # The welcome message
    DESCRIPTION = classpath.get_source("welcome.txt").read_text(encoding=Charset.UTF_8.val)

    # location of the .version file
    VERSION = Version.load(load_dir=classpath.source_path)

    # The resources folder
    RESOURCE_DIR = str(classpath.resource_path)

    def __init__(self, app_name: str):
        super().__init__(app_name, self.VERSION, self.DESCRIPTION.format(self.VERSION), resource_dir=self.RESOURCE_DIR)
        self.vault = Vault(self.RESOURCE_DIR)

    def _setup_arguments(self) -> None:
        # fmt: off
        self._with_chained_args('operation', 'the Vault operation to process') \
            .argument('list', 'list all entries matching the given filter criteria, if specified') \
                .add_parameter('filter', "filter the listed vault entries by it's name", nargs='*') \
            .argument('get', 'get a vault entry') \
                .add_parameter('name', 'the name of the vault entry which identifies it') \
                .add_parameter('show', 'boolean value. Indicates whether to show or copy to the clipboard', nargs='?') \
            .argument('del', 'delete an existing vault entry') \
                .add_parameter('name', 'the name of the vault entry which identifies it') \
            .argument('add', 'add a NEW UNIQUE vault entry') \
                .add_parameter('name', 'the name of the vault entry which identifies it') \
                .add_parameter('hint', 'applicable hints related to that vault entry', nargs='?') \
            .argument('upd', 'update an existing vault entry') \
                .add_parameter('name', 'the name of the vault entry which identifies it') \
                .add_parameter('hint', 'applicable hints related to that vault entry', nargs='?')  # fmt: on

    def _log_arguments(self) -> None:
        log.debug("Vault arguments parsed (values redacted)")

    def _main(self, *params, **kwargs) -> ExitStatus:
        """Run the application with the command line arguments"""
        log.info(
            dedent(
                f"""
        {self._app_name} v{self._app_version}

        Settings ==============================
                VAULT_USER: {VaultConfig.INSTANCE.vault_user}
                VAULT_FILE: {VaultConfig.INSTANCE.vault_file}
                STARTED: {now("%Y-%m-%d %H:%M:%S")}
        =======================================\n
        """
            )
        )

        hook_exit_signals(self._abort)

        return self._exec_application()

    def _cleanup(self) -> None:
        """Close and lock the vault"""
        if hasattr(self, "vault"):
            self.vault.discard()

    def _abort(self, signum=0, frame=None) -> None:
        """Unwind the active operation before releasing its lock and descriptors."""
        self.exit(signum, frame)

    def _exec_application(self) -> ExitStatus:
        """Execute the specified vault operation"""
        ret_val, op = 0, self.get_arg("operation")
        with self.vault.open() as unlocked:
            if not unlocked:
                raise VaultOpenError("Unable to open/unlock vault")
            if op == "add":
                self.vault.add(self.get_arg("name"), self.get_arg("hint"), None)
            elif op == "get":
                self.vault.get(self.get_arg("name"), self._show_passwd())
            elif op == "del":
                self.vault.remove(self.get_arg("name"))
            elif op == "upd":
                self.vault.update(self.get_arg("name"), self.get_arg("hint"), None)
            elif op == "list":
                self.vault.list(self.get_arg("filter"))
            else:
                ret_val = 1
                syserr(f"### Invalid operation: {op}")
                self.usage(ExitStatus.FAILED)

        return ExitStatus.of(ret_val)

    def _show_passwd(self) -> bool:
        """TODO"""
        return to_bool(self.get_arg("show"))


if __name__ == "__main__":
    # Application entry point
    Main("vault").INSTANCE.run(sys.argv[1:])
