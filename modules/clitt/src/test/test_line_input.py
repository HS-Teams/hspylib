#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import unittest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

from _test_setup import setup_test_environment

setup_test_environment()

from clitt.core.tui.line_input.keyboard_input import KeyboardInput
from hspylib.core.tools.commons import dirname

TEST_DIR = dirname(__file__)


class TestKeyboardInput(unittest.TestCase):
    # Setup tests
    def setUp(self):
        KeyboardInput._HISTORY = [""]
        KeyboardInput._UNDO_HISTORY.clear()
        KeyboardInput._REDO_HISTORY.clear()
        KeyboardInput._HIST_INDEX = 0

    # Teardown tests
    def tearDown(self):
        KeyboardInput._HISTORY = [""]

    # TEST CASES ----------

    def test_should_preserve_empty_first_history_entry(self):
        KeyboardInput._add_history("hello")
        self.assertEqual(KeyboardInput._HISTORY[-1], "")
        self.assertIn("hello", KeyboardInput._HISTORY)

    def test_should_not_store_short_inputs(self):
        KeyboardInput._add_history("hi")
        self.assertEqual(len(KeyboardInput._HISTORY), 1)

    def test_should_not_duplicate_existing_entries(self):
        KeyboardInput._add_history("command")
        KeyboardInput._add_history("command")
        count = KeyboardInput._HISTORY.count("command")
        self.assertEqual(count, 1)

    def test_should_support_undo_and_redo(self):
        kb = KeyboardInput()
        kb._update_input("first")
        kb._update_input("second")
        undone = KeyboardInput._undo()
        self.assertEqual(undone, "first")
        redone = KeyboardInput._redo()
        self.assertEqual(redone, "second")

    def test_should_render_suggestion_correctly(self):
        KeyboardInput._add_history("print hello")
        KeyboardInput._add_history("print world")
        kb = KeyboardInput()
        kb.text = "print"
        hint = kb._render_suggestions()
        self.assertEqual(hint, " hello")

    def test_should_navigate_history_correctly(self):
        for entry in ["one", "two", "three"]:
            KeyboardInput._add_history(entry)
        kb = KeyboardInput()
        kb.text = ""
        prev = kb._prev_in_history()
        next_ = kb._next_in_history()
        self.assertIsInstance(prev, str)
        self.assertIsInstance(next_, str)
        self.assertIn(next_, KeyboardInput._HISTORY)


# Program entry point.
if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestKeyboardInput)
    unittest.TextTestRunner(verbosity=2, failfast=True, stream=sys.stdout).run(suite)
