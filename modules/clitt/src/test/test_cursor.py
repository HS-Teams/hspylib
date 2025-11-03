#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unit tests for the terminal cursor helper."""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import call, patch

TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

from _test_setup import setup_test_environment

setup_test_environment()

# Remove runtime stubs so we can exercise the actual cursor implementation.
for module_name in ["clitt.core.term.cursor", "clitt.core.term.screen"]:
    sys.modules.pop(module_name, None)

from clitt.core.term.commons import Direction, Portion
from clitt.core.term.cursor import Cursor
from hspylib.modules.cli.vt100.vt_100 import Vt100


class CursorTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.cursor = Cursor()
        self.reset_cursor()

    def tearDown(self) -> None:
        self.reset_cursor()

    def reset_cursor(self) -> None:
        self.cursor.position = Cursor.CURSOR_HOME
        self.cursor._bottom = self.cursor.position
        self.cursor._saved_attrs = (self.cursor.position, self.cursor._bottom)


class TestCursorControlSequences(CursorTestCase):
    def test_should_emit_expected_control_sequences(self) -> None:
        self.cursor.position = (5, 5)
        self.cursor._bottom = self.cursor.position

        with patch("clitt.core.term.cursor.sysout") as mock_sysout:
            self.cursor.move_to(3, 4)
            self.cursor.move(2, Direction.RIGHT)
            self.cursor.erase(Portion.SCREEN)
            self.cursor.erase_line()
            saved_position = self.cursor.position
            saved_bottom = self.cursor._bottom

            self.cursor.save()
            self.cursor.position = (7, 7)
            self.cursor._bottom = (7, 7)
            self.cursor.restore()

        self.assertEqual(saved_position, self.cursor.position)
        self.assertEqual(saved_bottom, self.cursor._bottom)

        expected_calls = [
            call("%CUP(3;4)%", end=""),
            call(Direction.RIGHT.value[1].format(n=2), end=""),
            call(Portion.SCREEN.value[0], end=""),
            call(Direction.UP.value[1].format(n=1), end=""),
            call(Portion.LINE.value[0], end=""),
            call(Direction.LEFT.value[1].format(n=6), end=""),
            call(Vt100.save_cursor(), end=""),
            call(Vt100.restore_cursor(), end=""),
        ]
        self.assertEqual(expected_calls, mock_sysout.call_args_list)


class TestCursorWriteAndWriteln(CursorTestCase):
    def test_write_single_line_should_advance_columns(self) -> None:
        text = "Hello"
        cleaned = self.cursor.cleanup_text(text)
        text_offset = self.cursor.offset_text(cleaned)
        expected_row = self.cursor.position[0] + cleaned.count(os.linesep)
        expected_col = text_offset + (self.cursor.position[1] if cleaned.count(os.linesep) == 0 else 0)

        with patch("clitt.core.term.cursor.sysout"):
            new_position = self.cursor.write(text)

        self.assertEqual((expected_row, expected_col), new_position)
        self.assertEqual((expected_row, expected_col), self.cursor.position)

    def test_write_multi_line_should_move_to_next_row(self) -> None:
        self.cursor.position = (2, 3)
        text = "Hello" + os.linesep + "World"
        cleaned = self.cursor.cleanup_text(text)
        text_offset = self.cursor.offset_text(cleaned)
        expected_row = self.cursor.position[0] + cleaned.count(os.linesep)
        expected_col = text_offset + (self.cursor.position[1] if cleaned.count(os.linesep) == 0 else 0)

        with patch("clitt.core.term.cursor.sysout"):
            new_position = self.cursor.write(text)

        self.assertEqual((expected_row, expected_col), new_position)
        self.assertEqual((expected_row, expected_col), self.cursor.position)

    def test_writeln_should_ignore_color_placeholders(self) -> None:
        self.cursor.position = (4, 2)
        text = "%RED%Hi%NC%"
        prepared = self.cursor.cleanup_text(text + os.linesep)
        text_offset = self.cursor.offset_text(prepared)
        expected_row = self.cursor.position[0] + prepared.count(os.linesep)
        expected_col = text_offset + (self.cursor.position[1] if prepared.count(os.linesep) == 0 else 0)

        with patch("clitt.core.term.cursor.sysout"):
            new_position = self.cursor.writeln(text)

        self.assertEqual((expected_row, expected_col), new_position)
        self.assertEqual((expected_row, expected_col), self.cursor.position)


class TestCursorSaveRestore(CursorTestCase):
    def test_save_and_restore_should_restore_saved_attributes(self) -> None:
        self.cursor.position = (3, 6)
        self.cursor._bottom = (5, 8)
        saved_state = (self.cursor.position, self.cursor._bottom)

        with patch("clitt.core.term.cursor.sysout") as mock_sysout:
            self.cursor.save()
            self.assertEqual(saved_state, self.cursor._saved_attrs)

            self.cursor.position = (1, 1)
            self.cursor._bottom = (1, 1)
            self.cursor.restore()

        self.assertEqual(saved_state[0], self.cursor.position)
        self.assertEqual(saved_state[1], self.cursor._bottom)
        self.assertIn(call(Vt100.save_cursor(), end=""), mock_sysout.call_args_list)
        self.assertIn(call(Vt100.restore_cursor(), end=""), mock_sysout.call_args_list)


if __name__ == "__main__":
    unittest.main()
