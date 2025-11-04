#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import unittest
from dataclasses import dataclass
from typing import Callable, Optional
from unittest.mock import patch

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
if TEST_DIR not in sys.path:
    sys.path.insert(0, TEST_DIR)

from _test_setup import setup_test_environment

setup_test_environment()

from clitt.core.term.commons import Direction
from clitt.core.tui.tui_component import TUIComponent
from clitt.core.tui.tui_preferences import TUIPreferences
from hspylib.modules.cli.keyboard import Keyboard


class FakeCursor:
    def __init__(self) -> None:
        self.saved = 0
        self.ended = 0
        self.erased: list[Direction] = []
        self.reset = 0
        self.written: list[str] = []

    def save(self) -> None:
        self.saved += 1

    def end(self) -> None:
        self.ended += 1

    def erase(self, direction: Direction) -> None:
        self.erased.append(direction)

    def reset_mode(self) -> None:
        self.reset += 1

    def writeln(self, text: str) -> None:
        self.written.append(text)


class FakeColor:
    def __init__(self, code: str) -> None:
        self.code = code


@dataclass
class FakePreferences:
    selected_icon: str = "SELECTED"
    unselected_icon: str = "UNSELECTED"
    sel_bg_color: FakeColor = FakeColor("%SEL_BG%")
    highlight_color: FakeColor = FakeColor("%HIGHLIGHT%")
    text_color: FakeColor = FakeColor("%TEXT%")


class FakeScreen:
    def __init__(self, preferences: FakePreferences) -> None:
        self.cursor = FakeCursor()
        self.preferences = preferences
        self.lines = 24
        self.columns = 80
        self.watchers: list[Callable[[], None]] = []
        self.cleared = 0

    def add_watcher(self, watcher: Callable[[], None]) -> None:
        self.watchers.append(watcher)

    def clear(self) -> None:
        self.cleared += 1


class FakeTerminal:
    def __init__(self, screen: FakeScreen) -> None:
        self.screen = screen
        self.echo_calls: list[tuple[object, str, bool]] = []

    def echo(self, obj: object = "", end: str = os.linesep, markdown: bool = False) -> None:
        self.echo_calls.append((obj, end, markdown))


class _TestComponent(TUIComponent):
    def __init__(self) -> None:
        super().__init__("Test")
        self.render_calls = 0
        self.on_key: Optional[Callable[[Keyboard], None]] = None

    def render(self) -> None:
        self.render_calls += 1
        self._re_render = False

    def handle_keypress(self) -> Keyboard:
        key = Keyboard.wait_keystroke()
        if self.on_key:
            self.on_key(key)
        return key


class TestTUIComponent(unittest.TestCase):
    def setUp(self) -> None:
        from clitt.core.term.terminal import Terminal

        self._terminal_cls = Terminal
        self._original_terminal = Terminal.INSTANCE
        self._original_prefs = TUIPreferences.INSTANCE
        self.preferences = FakePreferences()
        TUIPreferences.INSTANCE = self.preferences

    def tearDown(self) -> None:
        from clitt.core.term.terminal import Terminal

        Terminal.INSTANCE = self._original_terminal
        TUIPreferences.INSTANCE = self._original_prefs

    def _create_component(self) -> tuple[_TestComponent, FakeScreen, FakeTerminal]:
        from clitt.core.term.terminal import Terminal

        screen = FakeScreen(self.preferences)
        terminal = FakeTerminal(screen)
        Terminal.INSTANCE = terminal
        component = _TestComponent()
        return component, screen, terminal

    def test_prepare_render_should_register_watcher_and_configure_terminal(self) -> None:
        component, screen, _ = self._create_component()

        with patch.object(self._terminal_cls, "set_auto_wrap") as mock_wrap, \
            patch.object(self._terminal_cls, "set_show_cursor") as mock_cursor:
            component._prepare_render(auto_wrap=True, show_cursor=True, clear_screen=True)

        self.assertIn(component.invalidate, screen.watchers)
        mock_wrap.assert_called_once_with(True)
        mock_cursor.assert_called_once_with(True)
        self.assertEqual(1, screen.cleared)
        self.assertEqual(1, screen.cursor.saved)

    def test_loop_should_stop_when_done_and_cleanup_cursor(self) -> None:
        component, screen, _ = self._create_component()

        def wait_side_effect() -> Keyboard:
            component._done = True
            return Keyboard.VK_NONE

        with patch.object(Keyboard, "wait_keystroke", side_effect=wait_side_effect) as mock_wait:
            result = component._loop()

        mock_wait.assert_called_once()
        self.assertEqual(Keyboard.VK_NONE, result)
        self.assertEqual(1, component.render_calls)
        self.assertEqual(1, screen.cursor.ended)
        self.assertEqual([Direction.DOWN], screen.cursor.erased)
        self.assertEqual(1, screen.cursor.reset)
        self.assertEqual([os.linesep], screen.cursor.written)

    def test_loop_should_return_break_key_without_setting_done(self) -> None:
        component, screen, _ = self._create_component()

        with patch.object(Keyboard, "wait_keystroke", side_effect=[Keyboard.VK_ESC]) as mock_wait:
            result = component._loop(break_keys=[Keyboard.VK_ESC])

        mock_wait.assert_called_once()
        self.assertEqual(Keyboard.VK_ESC, result)
        self.assertFalse(component._done)
        self.assertEqual(1, component.render_calls)
        self.assertEqual(1, screen.cursor.ended)

    def test_draw_selector_should_emit_expected_sequences(self) -> None:
        component, _, terminal = self._create_component()

        selector = component.draw_selector(is_selected=True, has_bg_color=True)

        self.assertEqual("SELECTED", selector)
        self.assertEqual(
            [
                ("%SEL_BG%", "", False),
                ("%HIGHLIGHT%", "", False),
            ],
            terminal.echo_calls,
        )

        terminal.echo_calls.clear()

        selector = component.draw_selector(is_selected=False)

        self.assertEqual("UNSELECTED", selector)
        self.assertEqual([("%TEXT%", "", False)], terminal.echo_calls)

    def test_draw_helpers_should_render_to_terminal(self) -> None:
        component, _, terminal = self._create_component()

        component.draw_navbar("NAVBAR")
        component.draw_line("Item {}", "value")

        self.assertEqual(
            [
                ("NAVBAR", "", False),
                ("Item value%NC%", os.linesep, False),
            ],
            terminal.echo_calls,
        )


if __name__ == "__main__":
    unittest.main()
