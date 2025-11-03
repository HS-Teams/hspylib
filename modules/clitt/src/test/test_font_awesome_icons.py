#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

from _test_setup import setup_test_environment

setup_test_environment()

from clitt.core.icons.font_awesome.app_icons import AppIcons
from clitt.core.icons.font_awesome.awesome import Awesome
from clitt.core.icons.font_awesome.form_icons import FormIcons
from clitt.core.icons.font_awesome.nav_icons import NavIcons
from clitt.core.icons.font_awesome.widget_icons import WidgetIcons
from clitt.core.tui.menu.tui_menu_item import TUIMenuItem
from clitt.core.term.terminal import Terminal


class TestAwesomeUtilities(unittest.TestCase):
    def test_no_icon_should_return_blank_placeholder(self) -> None:
        icon = Awesome.no_icon()

        self.assertEqual("NO_ICON", icon.name)
        self.assertEqual(" ", str(icon))
        self.assertEqual(1, len(icon))
        self.assertEqual(" ", format(icon, "s"))

    @patch("clitt.core.icons.font_awesome.awesome.sysout")
    def test_print_unicode_should_render_from_hex_string(self, mock_sysout) -> None:
        Awesome.print_unicode("2665")

        mock_sysout.assert_called_once_with("♥ ", end="")

    @patch("clitt.core.icons.font_awesome.awesome.sysout")
    def test_print_unicode_should_render_from_integer(self, mock_sysout) -> None:
        Awesome.print_unicode(0x2191, end="!")

        mock_sysout.assert_called_once_with("↑ ", end="!")

    def test_print_unicode_should_raise_type_error_on_invalid_data(self) -> None:
        with self.assertRaises(TypeError):
            Awesome.print_unicode("1F600")

        with self.assertRaises(TypeError):
            Awesome.print_unicode(object())


class TestFontAwesomeEnumerations(unittest.TestCase):
    def test_icon_enums_should_expose_expected_unicode(self) -> None:
        self.assertEqual("\u2191", NavIcons.UP.unicode)
        self.assertEqual("\uF432", NavIcons.POINTER.unicode)
        self.assertEqual("\uF408", AppIcons.GITHUB.unicode)
        self.assertEqual("\uF00C", FormIcons.CHECK.unicode)
        self.assertEqual("\uF198", WidgetIcons.WIDGET.unicode)

    def test_nav_icon_names_snapshot(self) -> None:
        expected_names = [
            "_CUSTOM",
            "UP",
            "RIGHT",
            "DOWN",
            "LEFT",
            "UP_DOWN",
            "LEFT_RIGHT",
            "ENTER",
            "TAB",
            "BACKSPACE",
            "POINTER",
            "SELECTED",
            "UNSELECTED",
            "BREADCRUMB",
        ]

        self.assertListEqual(NavIcons.names(), expected_names)


class TestMenuNavigationIcons(unittest.TestCase):
    def setUp(self) -> None:
        class _StubColor:
            def __init__(self, placeholder: str) -> None:
                self.placeholder = placeholder
                self.code = placeholder

        class _StubPreferences:
            def __init__(self) -> None:
                self.navbar_color = _StubColor("%NAVBAR%")
                self.breadcrumb_color = _StubColor("%BREADCRUMB%")
                self.tooltip_color = _StubColor("%TOOLTIP%")
                self.selected_icon = "*"
                self.unselected_icon = "-"
                self.sel_bg_color = SimpleNamespace(code="%SEL_BG%")
                self.highlight_color = SimpleNamespace(code="%HIGHLIGHT%")
                self.text_color = SimpleNamespace(code="%TEXT%")

        class _StubScreen:
            def __init__(self) -> None:
                self.lines = 30
                self.columns = 80
                self.preferences = _StubPreferences()
                self.cursor = SimpleNamespace()

        self._original_terminal = Terminal.INSTANCE
        Terminal.INSTANCE = SimpleNamespace(screen=_StubScreen())

    def tearDown(self) -> None:
        Terminal.INSTANCE = self._original_terminal

    def test_composed_nav_icons_should_render_in_navbar_tooltip(self) -> None:
        class _StubMenu:
            def __init__(self, title: str, tooltip: str) -> None:
                self._title = title
                self.tooltip = tooltip

            def __str__(self) -> str:
                return self._title

        menu = TUIMenuItem(title="Main", items=[_StubMenu("First", "First tooltip")])

        navbar = menu.navbar(to=len(menu.items))
        expected_icons = f"{NavIcons.UP}{NavIcons.DOWN}"

        self.assertIn(f"[{expected_icons}]", navbar)
        self.assertIn("%TOOLTIP%", navbar)
        self.assertIn("First tooltip", navbar)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
