#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
   @project: HsPyLib
   @package: hspylib.modules.application
      @file: application.py
   @created: Tue, 4 May 2021
    @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
      @site: https://github.com/yorevs/hspylib
   @license: MIT - Please refer to <https://opensource.org/licenses/MIT>

   Copyright·(c)·2024,·HSPyLib
"""
from abc import abstractmethod
from hspylib.core.config.app_config import AppConfigs
from hspylib.core.exception.exceptions import ApplicationError
from hspylib.core.metaclass.classpath import AnyPath
from hspylib.core.metaclass.singleton import AbstractSingleton
from hspylib.core.preconditions import check_state
from hspylib.core.tools.commons import hook_exit_signals, log_init, syserr, sysout
from hspylib.core.tools.text_tools import camelcase
from hspylib.core.zoned_datetime import now
from hspylib.modules.application.argparse.argument_parser import HSArgumentParser
from hspylib.modules.application.argparse.arguments_builder import ArgumentsBuilder
from hspylib.modules.application.argparse.chained_arguments_builder import ChainedArgumentsBuilder
from hspylib.modules.application.argparse.options_builder import OptionsBuilder
from hspylib.modules.application.exit_hooks import ExitHooks
from hspylib.modules.application.exit_status import ExitStatus
from hspylib.modules.application.version import Version
from textwrap import dedent
from typing import Any, Optional

import argparse
import atexit
import logging as log
import os
import sys
import traceback


class Application(metaclass=AbstractSingleton):
    """HsPyLib application framework. This is the base class for the HsPyLib applications."""

    INSTANCE = None
    CONFIG_CLASS = AppConfigs
    PARSER_CLASS = HSArgumentParser

    @staticmethod
    def _help_formatter(prog) -> argparse.HelpFormatter:
        return argparse.RawDescriptionHelpFormatter(prog, indent_increment=2, max_help_position=27)

    @staticmethod
    def exit(signum: int = 0, frame: Any = None, clear_screen: bool = False) -> None:
        """
        Handle interruptions to shutdown gracefully
        :param signum: The signal number or the exit http_code
        :param frame: The frame raised by the signal
        :param clear_screen: Whether to clean the screen before execution or not
        """
        if frame:
            log.warning("Signal handler hooked signum=%d frame=%s", signum, frame)
            exit_status = ExitStatus.ABORTED
        else:
            exit_status = ExitStatus.of(signum)
        if clear_screen:
            sysout("%ED2%%HOM%")

        sys.exit(exit_status.value)

    def __init__(
        self,
        name: str,
        version: Version,
        description: str = None,
        usage: str = None,
        epilog: str = None,
        resource_dir: AnyPath = None,
        log_dir: AnyPath = None,
    ):
        log.captureWarnings(True)
        hook_exit_signals(Application.exit)

        self.exit_hooks = ExitHooks(self._cleanup)
        self.exit_hooks.hook()
        self._root_dir = os.getcwd()
        self._args = {}
        self._exit_code = ExitStatus.NOT_SET
        self._app_name = name
        self._app_version = version
        self._app_description = description
        self._arg_parser = self.PARSER_CLASS(
            exit_on_error=False,
            prog=name,
            allow_abbrev=False,
            formatter_class=self._help_formatter,
            description=dedent(description or ""),
            usage=usage,
            epilog=dedent(epilog or ""),
        )
        self._arg_parser.add_argument("-v", "--version", action="version", version=f"%(prog)s v{self._app_version}")

        # Initialize application logs
        self._log_file = f"{log_dir or os.getenv('HHS_LOG_DIR', os.getcwd())}/{camelcase(name)}.log"
        check_state(log_init(filename=self._log_file), "Unable to initialize logging. log_file={}", self._log_file)

        # Initialize application configs
        if os.path.exists(f"{resource_dir}"):
            self.configs = self.CONFIG_CLASS(resource_dir=resource_dir)
        elif not resource_dir and os.path.exists(f"{self._root_dir}/resources/application.properties"):
            self.configs = self.CONFIG_CLASS(resource_dir=f"{self._root_dir}/resources")
        else:
            log.debug('Resource dir "%s" not found. AppConfigs will not be available!', resource_dir or "<none>")

    def run(self, *params, **kwargs) -> None:
        """Main entry point handler."""
        today = now()
        no_exit = "no_exit" in kwargs
        log.info("Application %s started %s", self._app_name, today)
        try:
            atexit.register(self._cleanup)
            self._setup_arguments()
            self._args = self._arg_parser.parse_args(*params)
            self._log_arguments()
            self._exit_code = self._main(*params, **kwargs)
        except argparse.ArgumentError as err:
            log.error("Application failed to execute %s => %s", today, err)
            self.usage(ExitStatus.FAILED, no_exit=True)
            syserr(f"\n### Error {self._app_name} -> {err}\n\n")
            raise ApplicationError(f"Application failed to execute => {err}") from err
        except Exception as err:
            _, _, tb = sys.exc_info()
            if tb:
                traceback.print_exc(file=sys.stderr)
            log.error("Application execution failed %s => %s", today, err)
            self._exit_code = ExitStatus.ERROR
            raise ApplicationError(f"Application execution failed => {err}") from err
        finally:
            log.info("Application %s finished %s", self._app_name, today)
            if self._exit_code == ExitStatus.NOT_SET:
                _, code, _ = sys.exc_info()
                self._exit_code = ExitStatus.of(code)
            if not no_exit:
                Application.exit(self._exit_code.val)

    def _log_arguments(self) -> None:
        """Allow applications handling secrets to suppress argument values."""
        log.debug("Command line arguments: %s", str(self._args))

    def usage(self, exit_code: ExitStatus = ExitStatus.SUCCESS, no_exit: bool = False) -> None:
        """Display the usage message and exit with the specified http_code ( or zero as default )
        :param no_exit: Do no exit the application on usage call
        :param exit_code: The exit http_code
        """
        self._exit_code = exit_code
        self._arg_parser.print_help(sys.stderr if self._exit_code != ExitStatus.SUCCESS else sys.stdout)
        if not no_exit:
            Application.exit(self._exit_code.val)

    def version(self) -> str:
        """Return the application version."""
        return str(self._app_version)

    def name(self) -> str:
        """Return the application name."""
        return self._app_name

    def get_arg(self, name: str) -> Optional[Any]:
        """Get the argument value specified by name."""
        return getattr(self._args, name) if self._args and hasattr(self._args, name) else None

    def _with_options(self) -> "OptionsBuilder":
        """Add options to the application."""
        return OptionsBuilder(self._arg_parser)

    def _with_arguments(self) -> "ArgumentsBuilder":
        """Add arguments to the application."""
        return ArgumentsBuilder(self._arg_parser)

    def _with_chained_args(self, arg: str, arg_help: str = None) -> "ChainedArgumentsBuilder":
        """Add chained arguments to the application."""
        return ChainedArgumentsBuilder(self._arg_parser, arg, arg_help)

    @abstractmethod
    def _setup_arguments(self) -> None:
        """Initialize application parameters and options."""

    @abstractmethod
    def _main(self, *params, **kwargs) -> ExitStatus:
        """Execute the application's main statements."""

    @abstractmethod
    def _cleanup(self) -> None:
        """Execute http_code cleanup before exiting."""
