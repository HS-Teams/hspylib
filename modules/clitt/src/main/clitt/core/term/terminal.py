#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
   @project: HsPyLib
   @package: hspylib.modules.cli.vt100
      @file: terminal.py
   @created: Tue, 11 May 2021
    @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
      @site: https://github.com/yorevs/hspylib
   @license: MIT - Please refer to <https://opensource.org/licenses/MIT>

   Copyright·(c)·2024,·HSPyLib
"""

import atexit
import logging as log
import os
import platform
import select
import shlex
import signal
from subprocess import CalledProcessError, PIPE, Popen
from typing import Any, Iterable, List, Optional, Tuple, TypeAlias

from clitt.core.exception.exceptions import NotATerminalError
from clitt.core.term.commons import is_a_tty
from clitt.core.term.cursor import Cursor
from clitt.core.term.screen import Screen
from hspylib.core.enums.charset import Charset
from hspylib.core.metaclass.singleton import Singleton
from hspylib.core.tools.commons import sysout
from hspylib.modules.application.exit_status import ExitStatus
from hspylib.modules.cli.keyboard import Keyboard
from hspylib.modules.cli.vt100.vt_100 import Vt100

TerminalExecResult: TypeAlias = Tuple[Optional[str], Optional[str], ExitStatus]


class Terminal(metaclass=Singleton):
    """Utility class to provide terminal features."""

    INSTANCE = None

    @staticmethod
    def is_a_tty() -> bool:
        return is_a_tty()

    @staticmethod
    def _chain_pipes(cmd_list: Iterable, **kwargs) -> Popen:
        """Run commands in PIPE, return the last process in chain.
        :param cmd_list: the command list to be executed.
        """
        if "stdout" in kwargs:
            del kwargs["stdout"]
        if "stderr" in kwargs:
            del kwargs["stderr"]
        if "stdin" in kwargs:
            del kwargs["stdin"]
        commands = map(shlex.split, cmd_list) if "shell" not in kwargs else cmd_list
        first_cmd, *rest_cmds = commands
        if len(rest_cmds) > 0:
            procs: List[Popen] = [Popen(first_cmd, stdout=PIPE, stderr=PIPE, **kwargs)]
            for cmd in rest_cmds:
                last_stdout = procs[-1].stdout
                procs.append(Popen(cmd, stdin=last_stdout, stdout=PIPE, stderr=PIPE, **kwargs))
            return procs[-1]
        return Popen(first_cmd, stdout=PIPE, stderr=PIPE, **kwargs)

    @staticmethod
    def shell_exec(cmd_line: str, **kwargs) -> TerminalExecResult:
        """Execute command with arguments and return it's run status.
        :param cmd_line: the command line to be executed.
        """
        proc = Terminal._chain_pipes(cmd_line.split("|"), **kwargs)
        log.info("Executing shell command: %s", cmd_line)
        output, err_out = proc.communicate()
        ret_code = ExitStatus.SUCCESS if proc.returncode == 0 else ExitStatus.FAILED
        log.info("Execution result: %s", ret_code)
        try:
            return (
                output.decode(Charset.UTF_8.val) if output else '',
                err_out.decode(Charset.UTF_8.val) if err_out else '',
                ret_code
            )
        except UnicodeDecodeError as err:
            return None, str(err), ExitStatus.ABNORMAL

    @staticmethod
    def shell_poll(cmd_line: str, **kwargs) -> None:
        """Execute command with arguments and continuously poll it's output.
        :param cmd_line: the command line to be executed.
        """
        if "stdout" in kwargs:
            del kwargs["stdout"]  # Deleted because it's forbidden
        if "stderr" in kwargs:
            del kwargs["stderr"]  # Deleted because it's forbidden
        if "shell" in kwargs:
            del kwargs["shell"]  # Deleted because we don't want to use it
        try:
            log.info("Polling shell command: %s", cmd_line)
            cmd_args = list(filter(None, shlex.split(cmd_line)))
            with Popen(cmd_args, stdout=PIPE, stderr=PIPE, **kwargs) as proc:
                process = select.poll()
                process.register(proc.stdout)
                process.register(proc.stderr)
                while not Keyboard.kbhit():
                    if poll_obj := process.poll(0.5):
                        line = proc.stdout.readline()
                        sysout(line.decode(Charset.UTF_8.val) if isinstance(line, bytes) else line.strip(), end="")
                        log.debug("Polling returned: %s", str(poll_obj))
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except (InterruptedError, KeyboardInterrupt):
            log.warning("Polling process has been interrupted command='%s'", cmd_line)
        except CalledProcessError as err:
            log.error("Command failed: %s => %s", cmd_line, err)

    @staticmethod
    def open(filename: str) -> None:
        """Open the specified file using the default editor."""
        my_os = os.environ.get("HHS_MY_OS", platform.system())
        if "Darwin" == my_os:
            Terminal.shell_exec(f"open {filename}")
        elif "Linux" == my_os:
            Terminal.shell_exec(f"xdg-open {filename}")
        else:
            raise NotImplementedError(f"OS '{my_os}' is not supported")

    @classmethod
    def restore(cls) -> None:
        """Clear the terminal and restore default attributes [wrap,cursor,echo]."""
        cls.set_attributes(show_cursor=True, auto_wrap=True, enable_echo=True)
        cls.alternate_screen(False)
        sysout("%MOD(0)%", end="")

    @classmethod
    def set_enable_echo(cls, enabled: bool = True) -> None:
        """Enable echo in the terminal.
        :param enabled: whether is enabled or not.
        """
        if not cls.is_a_tty():
            log.warning(NotATerminalError("set_enable_echo:: Requires a terminal (TTY)"))
            return

        os.popen(f"stty {'echo -raw' if enabled else 'raw -echo min 0'}").read()

    @classmethod
    def set_auto_wrap(cls, auto_wrap: bool = True) -> None:
        """Set auto-wrap mode in the terminal.
        :param auto_wrap: whether auto_wrap is set or not.
        """
        if not cls.is_a_tty():
            log.warning(NotATerminalError("set_auto_wrap:: Requires a terminal (TTY)"))
            return

        sysout(Vt100.set_auto_wrap(auto_wrap), end="")

    @classmethod
    def set_show_cursor(cls, show_cursor: bool = True) -> None:
        """Show or hide cursor in the terminal.
        :param show_cursor: whether to show or hide he cursor.
        """
        if not cls.is_a_tty():
            log.warning(NotATerminalError("set_show_cursor:: Requires a terminal (TTY)"))
            return

        sysout(Vt100.set_show_cursor(show_cursor), end="")

    @classmethod
    def set_attributes(cls, **attrs) -> None:
        """Wrapper to set all terminal attributes at once."""
        # fmt: off
        enable_echo = attrs.get('enable_echo')
        auto_wrap = attrs.get('auto_wrap')
        show_cursor = attrs.get('show_cursor')
        # fmt: on
        if enable_echo is not None:
            cls.set_enable_echo(enable_echo)
        if auto_wrap is not None:
            cls.set_auto_wrap(auto_wrap)
        if show_cursor is not None:
            cls.set_show_cursor(show_cursor)

    @classmethod
    def clear(cls) -> None:
        """Clear terminal and move the cursor to HOME position (0, 0)."""
        cls.INSTANCE.screen.clear()

    @classmethod
    def echo(cls, obj: Any = "", end: str = os.linesep, markdown: bool = False) -> None:
        """Write the string representation of the object to the screen.
        :param obj the object to be written.
        :param end string appended after the last value, default a newline.
        :param markdown: whether to print a markdown render.
        """
        cls.INSTANCE.screen.cursor.write(obj, end=end, markdown=markdown)

    @classmethod
    def alternate_screen(cls, enable: bool) -> None:
        """Switch to the alternate screen buffer on/off."""
        cls.INSTANCE.screen.alternate = enable

    def __init__(self):
        self._screen = Screen.INSTANCE or Screen()
        atexit.register(self.restore)

    @property
    def screen(self) -> Screen:
        return self._screen

    @property
    def cursor(self) -> Cursor:
        return self.screen.cursor


assert (terminal := Terminal().INSTANCE) is not None, "Failed to create Terminal instance"

if __name__ == '__main__':
    print(terminal.shell_exec("cat /Users/hugo/Downloads/.DS_Store", shell=True))

