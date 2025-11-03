#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

from _test_setup import setup_test_environment

setup_test_environment()

from clitt.core.tui.tui_preferences import TUIPreferences
from clitt.core.icons.font_awesome.nav_icons import NavIcons
from hspylib.modules.cli.vt100.vt_color import VtColor
from hspylib.core.exception.exceptions import InvalidArgumentError
from hspylib.core.tools.text_tools import environ_name


class TestPreferences(unittest.TestCase):

    def setUp(self):
        self.preferences = TUIPreferences()
        self.preferences._overrides.clear()

    def tearDown(self):
        self.preferences._overrides.clear()

    def test_getitem_returns_current_preference_value(self):
        self.preferences["hhs.clitt.max.rows"] = 12
        self.assertEqual(12, self.preferences["hhs.clitt.max.rows"])

    def test_setitem_requires_matching_types(self):
        with self.assertRaises(InvalidArgumentError):
            self.preferences["hhs.clitt.max.rows"] = "twelve"

    def test_iteration_yields_override_keys(self):
        self.preferences["hhs.clitt.max.rows"] = 15
        self.preferences["hhs.clitt.items.per.line"] = 4

        keys = list(self.preferences)

        self.assertCountEqual(["hhs.clitt.max.rows", "hhs.clitt.items.per.line"], keys)

    def test_environment_override_casts_primitives(self):
        env_name = environ_name("hhs.clitt.max.rows")
        with patch.dict(os.environ, {env_name: "25"}, clear=False):
            self.preferences._overrides.clear()
            self.assertEqual(25, self.preferences.max_rows)

    def test_environment_override_casts_enums(self):
        env_name = environ_name("hhs.clitt.title.color")
        with patch.dict(os.environ, {env_name: "green"}, clear=False):
            self.preferences._overrides.clear()
            self.assertEqual(VtColor.GREEN, self.preferences.title_color)

    def test_max_rows_and_items_per_line_are_clamped(self):
        self.preferences["hhs.clitt.max.rows"] = 1
        self.preferences["hhs.clitt.items.per.line"] = 1

        self.assertEqual(3, self.preferences.max_rows)
        self.assertEqual(2, self.preferences.items_per_line)

    def test_icon_and_color_fallbacks_are_used_on_invalid_environment_override(self):
        icon_env = environ_name("hhs.clitt.selected.icon")
        color_env = environ_name("hhs.clitt.success.color")
        with patch.dict(os.environ, {icon_env: "not_an_icon", color_env: "not_a_color"}, clear=False):
            self.preferences._overrides.clear()
            self.assertEqual(NavIcons.POINTER, self.preferences.selected_icon)
            self.assertEqual(VtColor.GREEN, self.preferences.success_color)


if __name__ == "__main__":
    unittest.main()
