#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unit tests for terminal commons helpers."""

import termios
import unittest
from unittest.mock import MagicMock, patch

import sys
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

from _test_setup import setup_test_environment

setup_test_environment()

from clitt.core.term.commons import Direction, Portion, get_cursor_position, get_dimensions, is_a_tty


class TestTerminalCommonsEnvironment(unittest.TestCase):
    def test_is_a_tty_should_fallback_when_stdin_is_not_tty(self) -> None:
        fallback = (99, 88)

        with patch("clitt.core.term.commons.sys.stdout", new=MagicMock()) as mock_stdout, \
            patch("clitt.core.term.commons.sys.stdin", new=MagicMock()) as mock_stdin, \
            patch("clitt.core.term.commons.get_terminal_size") as mock_get_terminal_size:

            mock_stdout.isatty.return_value = True
            mock_stdin.isatty.return_value = False

            self.assertFalse(is_a_tty())

            dimensions = get_dimensions(fallback)

        self.assertEqual(2, mock_stdout.isatty.call_count)
        self.assertEqual(2, mock_stdin.isatty.call_count)
        mock_get_terminal_size.assert_not_called()
        self.assertEqual(fallback, dimensions)

    def test_is_a_tty_should_ignore_stdin_value_error(self) -> None:
        with patch("clitt.core.term.commons.sys.stdout", new=MagicMock()) as mock_stdout, \
            patch("clitt.core.term.commons.sys.stdin", new=MagicMock()) as mock_stdin:

            mock_stdout.isatty.return_value = True
            mock_stdin.isatty.side_effect = ValueError()

            self.assertTrue(is_a_tty())

        self.assertEqual(2, mock_stdout.isatty.call_count)
        self.assertEqual(1, mock_stdin.isatty.call_count)


class TestCursorPosition(unittest.TestCase):
    def test_get_cursor_position_should_return_fallback_when_debugging(self) -> None:
        fallback = (5, 5)

        with patch("clitt.core.term.commons.is_debugging", return_value=True) as mock_debug, \
            patch("clitt.core.term.commons.is_a_tty") as mock_is_tty, \
            patch("clitt.core.term.commons.sys.stdin") as mock_stdin, \
            patch("clitt.core.term.commons.termios.tcgetattr") as mock_tcgetattr, \
            patch("clitt.core.term.commons.termios.tcsetattr") as mock_tcsetattr:

            result = get_cursor_position(fallback)

        self.assertEqual(fallback, result)
        mock_debug.assert_called_once()
        mock_is_tty.assert_not_called()
        mock_stdin.read.assert_not_called()
        mock_tcgetattr.assert_not_called()
        mock_tcsetattr.assert_not_called()

    def test_get_cursor_position_should_return_fallback_when_not_tty(self) -> None:
        fallback = (7, 7)

        with patch("clitt.core.term.commons.is_debugging", return_value=False) as mock_debug, \
            patch("clitt.core.term.commons.is_a_tty", return_value=False) as mock_is_tty, \
            patch("clitt.core.term.commons.sys.stdin") as mock_stdin, \
            patch("clitt.core.term.commons.termios.tcgetattr") as mock_tcgetattr:

            result = get_cursor_position(fallback)

        self.assertEqual(fallback, result)
        mock_debug.assert_called_once()
        mock_is_tty.assert_called_once()
        mock_stdin.read.assert_not_called()
        mock_tcgetattr.assert_not_called()

    def test_get_cursor_position_should_parse_terminal_response(self) -> None:
        response = "\x1b[12;34R"
        fallback = (0, 0)
        attrs = ["attrs"]

        mock_stdout = MagicMock()
        mock_stdin = MagicMock()
        mock_stdin.fileno.return_value = 3
        mock_stdin.read.side_effect = list(response)

        with patch("clitt.core.term.commons.is_debugging", return_value=False) as mock_debug, \
            patch("clitt.core.term.commons.is_a_tty", return_value=True) as mock_is_tty, \
            patch("clitt.core.term.commons.sys.stdout", new=mock_stdout), \
            patch("clitt.core.term.commons.sys.stdin", new=mock_stdin), \
            patch("clitt.core.term.commons.termios.tcgetattr", return_value=attrs) as mock_tcgetattr, \
            patch("clitt.core.term.commons.termios.tcsetattr") as mock_tcsetattr, \
            patch("clitt.core.term.commons.tty.setcbreak") as mock_setcbreak, \
            patch("clitt.core.term.commons.Vt100.get_cursor_pos", return_value="%GETPOS%") as mock_get_cursor_pos:

            result = get_cursor_position(fallback)

        self.assertEqual((12, 34), result)
        mock_debug.assert_called_once()
        mock_is_tty.assert_called_once()
        mock_get_cursor_pos.assert_called_once_with()
        mock_stdout.write.assert_called_once_with("%GETPOS%")
        mock_stdout.flush.assert_called_once_with()
        mock_setcbreak.assert_called_once_with(mock_stdin.fileno.return_value, termios.TCSANOW)
        mock_tcgetattr.assert_called_once_with(mock_stdin.fileno.return_value)
        mock_tcsetattr.assert_called_once_with(mock_stdin.fileno.return_value, termios.TCSANOW, attrs)
        self.assertEqual(len(response), mock_stdin.read.call_count)


class TestDirectionAndPortionEnums(unittest.TestCase):
    def test_direction_values_should_match_control_sequences(self) -> None:
        expected = {
            Direction.UP: ("%ED1%", "%CUU({n})%"),
            Direction.RIGHT: ("%EL0%", "%CUF({n})%"),
            Direction.DOWN: ("%ED0%", "%CUD({n})%"),
            Direction.LEFT: ("%EL1%", "%CUB({n})%"),
        }

        for direction, value in expected.items():
            self.assertEqual(value, direction.value)

    def test_portion_values_should_match_control_sequences(self) -> None:
        expected = {
            Portion.SCREEN: ("%ED2%", ""),
            Portion.LINE: ("%EL2%", ""),
        }

        for portion, value in expected.items():
            self.assertEqual(value, portion.value)


if __name__ == "__main__":
    unittest.main()
