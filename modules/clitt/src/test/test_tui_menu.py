#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import unittest
from pathlib import Path
from typing import Optional
from types import SimpleNamespace
from unittest.mock import Mock, patch

TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

from _test_setup import setup_test_environment

setup_test_environment()

from clitt.core.tui.menu.tui_menu import TUIMenu
from clitt.core.tui.menu.tui_menu_action import TUIMenuAction
from clitt.core.tui.menu.tui_menu_factory import TUIMenuFactory
from clitt.core.tui.menu.tui_menu_item import TUIMenuItem
from clitt.core.tui.menu.tui_menu_view import TUIMenuView
from clitt.core.tui.minput.input_validator import InputValidator
from clitt.core.tui.menu.tui_menu_ui import TUIMenuUi
from clitt.core.tui.tui_preferences import TUIPreferences
from clitt.core.term.terminal import Terminal


def _install_terminal_stub() -> None:
    cursor = SimpleNamespace(
        erase=lambda *_, **__: None,
        writeln=lambda *_, **__: None,
        write=lambda *_, **__: None,
        save=lambda *_, **__: None,
        restore=lambda *_, **__: None,
        move=lambda *_, **__: None,
        track=lambda *_, **__: None,
        end=lambda *_, **__: None,
        reset_mode=lambda *_, **__: None,
        home=lambda *_, **__: None,
    )
    preferences = TUIPreferences()
    screen = SimpleNamespace(
        lines=25,
        columns=80,
        cursor=cursor,
        preferences=preferences,
        add_watcher=lambda *_, **__: None,
        clear=lambda: None,
    )

    class _TerminalStub:
        def __init__(self, screen_ref):
            self.screen = screen_ref

        def echo(self, *_, **__):
            pass

    Terminal.INSTANCE = _TerminalStub(screen)
    TUIMenuUi.SCREEN = screen
    TUIMenuUi.PREFS = preferences
    TUIMenuUi.MENU_LINE = f"{'--' * TUIMenuUi.PREFS.title_line_length}"
    TUIMenuUi.MENU_TITLE_FMT = (
        f"{TUIMenuUi.PREFS.title_color}"
        f"+{TUIMenuUi.MENU_LINE}+%EOL%"
        "|{title:^" + str(2 * TUIMenuUi.PREFS.title_line_length) + "s}|%EOL%"
        f"+{TUIMenuUi.MENU_LINE}+%EOL%%NC%"
    )


_install_terminal_stub()


class TestTuiMenu(unittest.TestCase):

    def test_prompt_uses_default_dest_and_validator(self):
        captured_fields: list = []

        def fake_minput(form_fields):
            captured_fields.append(form_fields)
            return "result"

        with patch("clitt.core.tui.menu.tui_menu.minput", side_effect=fake_minput) as mock_minput:
            result = TUIMenu.prompt("Full Name")

        self.assertEqual("result", result)
        mock_minput.assert_called_once()
        self.assertEqual(1, len(captured_fields))
        self.assertEqual(1, len(captured_fields[0]))
        field = captured_fields[0][0]
        self.assertEqual("Full Name", field.label)
        self.assertEqual("Full Name", field.dest)
        self.assertEqual(InputValidator.words().pattern_type, field.input_validator.pattern_type)
        self.assertEqual(1, field.min_length)
        self.assertEqual(32, field.max_length)

    def test_prompt_accepts_custom_validator_and_dest(self):
        captured_fields: list = []
        validator = InputValidator.letters()

        def fake_minput(form_fields):
            captured_fields.append(form_fields)
            return "custom"

        with patch("clitt.core.tui.menu.tui_menu.minput", side_effect=fake_minput) as mock_minput:
            result = TUIMenu.prompt("User", dest="username", min_length=2, max_length=10, validator=validator)

        self.assertEqual("custom", result)
        mock_minput.assert_called_once()
        field = captured_fields[0][0]
        self.assertEqual("username", field.dest)
        self.assertIs(field.input_validator, validator)
        self.assertEqual(2, field.min_length)
        self.assertEqual(10, field.max_length)

    def test_factory_builders_create_nested_menu_tree(self):
        callbacks: list[Optional[TUIMenu]] = []

        def save_cb(menu: TUIMenu) -> Optional[TUIMenu]:
            callbacks.append(menu)
            return menu

        def reset_cb(menu: TUIMenu) -> Optional[TUIMenu]:
            callbacks.append(None)
            return None

        def quit_cb(menu: TUIMenu) -> Optional[TUIMenu]:
            callbacks.append(menu.parent)
            return menu.parent

        factory = (
            TUIMenuFactory.create_main_menu("Main")
            .with_item("Settings", "Adjust settings")
                .with_action("Save", "Persist changes").on_trigger(save_cb)
                .with_view("About", "About view").on_render("About content")
                .with_item("Advanced", "Advanced settings")
                    .with_action("Reset", "Reset to defaults").on_trigger(reset_cb)
                    .then()
                .then()
            .with_action("Quit", "Exit").on_trigger(quit_cb)
            .then()
        )

        main_menu = factory.build()

        self.assertIsInstance(main_menu, TUIMenuItem)
        self.assertEqual("Main", main_menu.title)
        self.assertEqual(2, len(main_menu.items))

        settings, quit_action = main_menu.items
        self.assertIsInstance(settings, TUIMenuItem)
        self.assertEqual("Settings", settings.title)
        self.assertEqual(3, len(settings.items))

        save_action, about_view, advanced_item = settings.items
        self.assertIsInstance(save_action, TUIMenuAction)
        self.assertIs(save_action._on_trigger, save_cb)

        self.assertIsInstance(about_view, TUIMenuView)
        self.assertEqual("About content", about_view._content)
        self.assertEqual(about_view._display_content, about_view._on_render)

        self.assertIsInstance(advanced_item, TUIMenuItem)
        self.assertEqual("Advanced", advanced_item.title)
        self.assertEqual(1, len(advanced_item.items))
        reset_action = advanced_item.items[0]
        self.assertIsInstance(reset_action, TUIMenuAction)
        self.assertIs(reset_action._on_trigger, reset_cb)

        self.assertIsInstance(quit_action, TUIMenuAction)
        self.assertIs(quit_action._on_trigger, quit_cb)

    def test_view_render_switches_between_content_and_callbacks(self):
        parent_menu = TUIMenuItem(title="Parent")
        view = TUIMenuView(parent_menu, title="Details")

        with patch.object(TUIMenuUi, "render_app_title") as mock_title, \
            patch.object(view, "draw_navbar") as mock_navbar:
            display_mock = Mock()
            view._display_content = display_mock
            view.on_render("Custom text")

            view.render()

            mock_title.assert_called_once()
            display_mock.assert_called_once_with()
            mock_navbar.assert_called_once_with(view.navbar())
            self.assertEqual("Custom text", view._content)

        with patch.object(TUIMenuUi, "render_app_title") as mock_title, \
            patch.object(view, "draw_navbar") as mock_navbar:
            custom_hook = Mock()
            view.on_render(custom_hook)

            view.render()

            mock_title.assert_called_once()
            custom_hook.assert_called_once_with()
            mock_navbar.assert_called_once_with(view.navbar())
            self.assertEqual(f"This is a view: {view.title}", view._content)


if __name__ == "__main__":
    unittest.main()
