#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

from _test_setup import setup_test_environment

setup_test_environment()

from clitt.core.tui.mchoose.menu_choose import MenuChoose
from hspylib.modules.cli.keyboard import Keyboard


class TestMenuChoose(unittest.TestCase):
    def setUp(self):
        self.cursor = MagicMock()
        self.cursor.move.return_value = None
        self.cursor.erase.return_value = None

        self.preferences = MagicMock()
        self.preferences.max_rows = 3

        self.screen = MagicMock()
        self.screen.cursor = self.cursor
        self.screen.lines = 20
        self.screen.preferences = self.preferences
        self.screen.add_watcher = MagicMock()
        self.screen.clear = MagicMock()

        self.terminal = MagicMock()
        self.terminal.screen = self.screen
        self.terminal.echo = MagicMock()

        self.terminal_patcher = patch("clitt.core.tui.tui_component.Terminal.INSTANCE", self.terminal)
        self.terminal_patcher.start()
        self.addCleanup(self.terminal_patcher.stop)

    @staticmethod
    def _create_menu(items, checked=False, max_rows=3):
        with patch.object(MenuChoose, "_max_rows", return_value=max_rows):
            return MenuChoose("Test Menu", items, checked)

    def test_navigation_updates_indices(self):
        menu = self._create_menu([f"Item {i}" for i in range(1, 13)])

        key_sequence = [
            Keyboard.VK_DOWN,
            Keyboard.VK_DOWN,
            Keyboard.VK_DOWN,
            Keyboard.VK_UP,
            Keyboard.VK_UP,
            Keyboard.VK_UP,
            Keyboard.VK_TAB,
            Keyboard.VK_SHIFT_TAB,
            Keyboard.VK_ONE,
            Keyboard.VK_TWO,
        ]

        states = []
        with patch("clitt.core.tui.mchoose.menu_choose.Keyboard.wait_keystroke", side_effect=key_sequence):
            for _ in range(len(key_sequence) - 1):
                menu.handle_keypress()
                states.append((menu.sel_index, menu.show_from, menu.show_to))

        expected_states = [
            (1, 0, 3),
            (2, 0, 3),
            (3, 1, 4),
            (2, 1, 4),
            (1, 1, 4),
            (0, 0, 3),
            (3, 3, 6),
            (0, 0, 3),
            (11, 9, 12),
        ]

        self.assertListEqual(states, expected_states)

    def test_space_and_invert_toggle_and_execute_returns_selected(self):
        items = ["alpha", "beta", "gamma"]
        menu = self._create_menu(items)

        with patch("clitt.core.tui.mchoose.menu_choose.Keyboard.wait_keystroke", return_value=Keyboard.VK_SPACE):
            menu.handle_keypress()
        self.assertListEqual(menu.sel_options, [1, 0, 0])

        with patch("clitt.core.tui.mchoose.menu_choose.Keyboard.wait_keystroke", return_value=Keyboard.VK_I):
            menu.handle_keypress()
        self.assertListEqual(menu.sel_options, [0, 1, 1])

        menu.sel_options = [0, 1, 1]
        with patch.object(menu, "_prepare_render"), patch.object(menu, "_loop", return_value=Keyboard.VK_ENTER):
            result = menu.execute()

        self.assertListEqual(result, [items[1], items[2]])

    def test_execute_handles_empty_and_single_item(self):
        menu = self._create_menu(["placeholder"])
        menu.items = []
        menu.sel_options = []
        self.assertIsNone(menu.execute())

        single_menu = self._create_menu(["only"], checked=True)
        single_menu.sel_options = [True]
        with patch.object(single_menu, "_prepare_render"), patch.object(
            single_menu, "_loop", return_value=Keyboard.VK_ENTER
        ):
            result = single_menu.execute()

        self.assertListEqual(result, ["only"])


if __name__ == "__main__":
    unittest.main()
