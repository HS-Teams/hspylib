#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import signal
import sys
import unittest
from pathlib import Path
from subprocess import PIPE
from unittest.mock import MagicMock, PropertyMock, patch

TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

from _test_setup import setup_test_environment

setup_test_environment()

from clitt.core.term.screen import Screen
from clitt.core.term.terminal import Terminal
from hspylib.modules.application.exit_status import ExitStatus


class TestTerminalAttributes(unittest.TestCase):
    @patch.object(Terminal, "is_a_tty", return_value=False)
    def test_set_enable_echo_should_guard_when_not_tty(self, mock_is_tty):
        with patch("clitt.core.term.terminal.os.popen") as mock_popen:
            Terminal.set_enable_echo(True)

        mock_is_tty.assert_called_once()
        mock_popen.assert_not_called()

    @patch.object(Terminal, "is_a_tty", return_value=True)
    def test_set_enable_echo_should_invoke_stty_when_tty(self, mock_is_tty):
        with patch("clitt.core.term.terminal.os.popen") as mock_popen:
            mock_popen.return_value.read.return_value = ""
            Terminal.set_enable_echo(False)

        mock_is_tty.assert_called_once()
        mock_popen.assert_called_once_with("stty raw -echo min 0")
        mock_popen.return_value.read.assert_called_once_with()

    @patch.object(Terminal, "is_a_tty", return_value=False)
    def test_set_auto_wrap_should_guard_when_not_tty(self, mock_is_tty):
        with patch("clitt.core.term.terminal.sysout") as mock_sysout:
            Terminal.set_auto_wrap(True)

        mock_is_tty.assert_called_once()
        mock_sysout.assert_not_called()

    @patch.object(Terminal, "is_a_tty", return_value=True)
    def test_set_auto_wrap_should_emit_escape_sequence_when_tty(self, mock_is_tty):
        with patch("clitt.core.term.terminal.sysout") as mock_sysout, \
            patch("clitt.core.term.terminal.Vt100.set_auto_wrap", return_value="%WRAP%") as mock_vt100:
            Terminal.set_auto_wrap(False)

        mock_is_tty.assert_called_once()
        mock_vt100.assert_called_once_with(False)
        mock_sysout.assert_called_once_with("%WRAP%", end="")

    @patch.object(Terminal, "is_a_tty", return_value=False)
    def test_set_show_cursor_should_guard_when_not_tty(self, mock_is_tty):
        with patch("clitt.core.term.terminal.sysout") as mock_sysout:
            Terminal.set_show_cursor(True)

        mock_is_tty.assert_called_once()
        mock_sysout.assert_not_called()

    @patch.object(Terminal, "is_a_tty", return_value=True)
    def test_set_show_cursor_should_emit_escape_sequence_when_tty(self, mock_is_tty):
        with patch("clitt.core.term.terminal.sysout") as mock_sysout, \
            patch("clitt.core.term.terminal.Vt100.set_show_cursor", return_value="%CURSOR%") as mock_cursor:
            Terminal.set_show_cursor(False)

        mock_is_tty.assert_called_once()
        mock_cursor.assert_called_once_with(False)
        mock_sysout.assert_called_once_with("%CURSOR%", end="")

    def test_should_set_enable_echo_only_when_provided(self):
        with patch.object(Terminal, "set_enable_echo") as mock_enable, \
            patch.object(Terminal, "set_auto_wrap") as mock_wrap, \
            patch.object(Terminal, "set_show_cursor") as mock_cursor:
            Terminal.set_attributes(enable_echo=True)

        mock_enable.assert_called_once_with(True)
        mock_wrap.assert_not_called()
        mock_cursor.assert_not_called()

    def test_should_set_auto_wrap_only_when_provided(self):
        with patch.object(Terminal, "set_enable_echo") as mock_enable, \
            patch.object(Terminal, "set_auto_wrap") as mock_wrap, \
            patch.object(Terminal, "set_show_cursor") as mock_cursor:
            Terminal.set_attributes(auto_wrap=False)

        mock_enable.assert_not_called()
        mock_wrap.assert_called_once_with(False)
        mock_cursor.assert_not_called()

    def test_should_set_show_cursor_only_when_provided(self):
        with patch.object(Terminal, "set_enable_echo") as mock_enable, \
            patch.object(Terminal, "set_auto_wrap") as mock_wrap, \
            patch.object(Terminal, "set_show_cursor") as mock_cursor:
            Terminal.set_attributes(show_cursor=True)

        mock_enable.assert_not_called()
        mock_wrap.assert_not_called()
        mock_cursor.assert_called_once_with(True)


class TestTerminalShellOperations(unittest.TestCase):
    @patch("clitt.core.term.terminal.Popen")
    def test_chain_pipes_should_pipe_commands(self, mock_popen):
        first_proc = MagicMock()
        second_proc = MagicMock()
        first_proc.stdout = MagicMock(name="first_stdout")
        second_proc.stdout = MagicMock(name="second_stdout")
        mock_popen.side_effect = [first_proc, second_proc]

        result = Terminal._chain_pipes(["echo 1", "grep 1"])

        self.assertIs(result, second_proc)
        self.assertEqual(mock_popen.call_count, 2)
        first_call, second_call = mock_popen.call_args_list
        self.assertEqual(first_call.args[0], ["echo", "1"])
        self.assertEqual(first_call.kwargs, {"stdout": PIPE, "stderr": PIPE})
        self.assertEqual(second_call.args[0], ["grep", "1"])
        self.assertEqual(
            second_call.kwargs,
            {"stdin": first_proc.stdout, "stdout": PIPE, "stderr": PIPE},
        )

    @patch.object(Terminal, "_chain_pipes")
    def test_shell_exec_should_decode_successful_output(self, mock_chain):
        proc = MagicMock()
        proc.communicate.return_value = (b"output", b"error")
        proc.returncode = 0
        mock_chain.return_value = proc

        stdout, stderr, status = Terminal.shell_exec("ls -l")

        mock_chain.assert_called_once_with(["ls -l"])
        self.assertEqual("output", stdout)
        self.assertEqual("error", stderr)
        self.assertEqual(ExitStatus.SUCCESS, status)

    @patch.object(Terminal, "_chain_pipes")
    def test_shell_exec_should_handle_unicode_errors(self, mock_chain):
        proc = MagicMock()
        proc.communicate.return_value = (b"\xff", b"")
        proc.returncode = 1
        mock_chain.return_value = proc

        stdout, stderr, status = Terminal.shell_exec("cat file")

        mock_chain.assert_called_once_with(["cat file"])
        self.assertIsNone(stdout)
        self.assertIn("'utf-8' codec can't decode", stderr)
        self.assertEqual(ExitStatus.ABNORMAL, status)

    @patch("clitt.core.term.terminal.os.killpg")
    @patch("clitt.core.term.terminal.os.getpgid", return_value=789)
    @patch("clitt.core.term.terminal.Keyboard.kbhit")
    @patch("clitt.core.term.terminal.sysout")
    @patch("clitt.core.term.terminal.select.poll")
    @patch("clitt.core.term.terminal.Popen")
    def test_shell_poll_should_stream_decoded_output(
        self,
        mock_popen,
        mock_poll,
        mock_sysout,
        mock_kbhit,
        mock_getpgid,
        mock_killpg,
    ):
        process = MagicMock()
        process.stderr = MagicMock(name="stderr")
        process.stdout = MagicMock(name="stdout")
        process.stdout.readline.return_value = b"hello\n"
        process.pid = 123

        context_manager = MagicMock()
        context_manager.__enter__.return_value = process
        context_manager.__exit__.return_value = None
        mock_popen.return_value = context_manager

        poller = MagicMock()
        poller.poll.side_effect = [[1], []]
        mock_poll.return_value = poller

        mock_kbhit.side_effect = [False, True]

        Terminal.shell_poll(
            "ls -l",
            stdout="ignored",
            stderr="ignored",
            shell=True,
            cwd="/tmp",
        )

        mock_popen.assert_called_once_with(["ls", "-l"], stdout=PIPE, stderr=PIPE, cwd="/tmp")
        poller.register.assert_any_call(process.stdout)
        poller.register.assert_any_call(process.stderr)
        mock_sysout.assert_called_with("hello\n", end="")
        mock_getpgid.assert_called_once_with(process.pid)
        mock_killpg.assert_called_once_with(789, signal.SIGTERM)


class TestTerminalScreenDelegation(unittest.TestCase):
    def test_alternate_screen_should_delegate_to_screen_singleton(self):
        with patch.object(Screen, "alternate", new_callable=PropertyMock) as mock_alternate:
            Terminal.alternate_screen(True)

        mock_alternate.assert_called_with(True)

    @patch.object(Terminal, "set_show_cursor")
    @patch.object(Terminal, "set_auto_wrap")
    @patch.object(Terminal, "set_enable_echo")
    def test_restore_should_reset_screen_through_singleton(
        self, mock_echo, mock_wrap, mock_cursor
    ):
        with patch.object(Screen, "alternate", new_callable=PropertyMock) as mock_alternate, \
            patch("clitt.core.term.terminal.sysout") as mock_sysout:
            Terminal.restore()

        mock_echo.assert_called_once_with(True)
        mock_wrap.assert_called_once_with(True)
        mock_cursor.assert_called_once_with(True)
        mock_alternate.assert_called_with(False)
        mock_sysout.assert_called_once_with("%MOD(0)%", end="")

if __name__ == "__main__":
    unittest.main()
