#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

from _test_setup import setup_test_environment

setup_test_environment()

from clitt.core.term.terminal import Terminal


class TestTerminalAttributes(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
