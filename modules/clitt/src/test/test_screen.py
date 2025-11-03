#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unit tests for the Screen singleton."""

import unittest
from unittest.mock import MagicMock, patch

import sys
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

from _test_setup import setup_test_environment

setup_test_environment()

# Replace the stubbed screen module with the real implementation so we can test it.
if "clitt.core.term.screen" in sys.modules:
    del sys.modules["clitt.core.term.screen"]

from clitt.core.term.commons import Portion
from clitt.core.term.screen import Screen


class ScreenTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.screen = Screen.INSTANCE if hasattr(Screen, "INSTANCE") else Screen()
        self.original_cursor = self.screen._cursor
        self.original_dimension = self.screen._dimension
        self.original_resize_timer = self.screen._resize_timer
        self.original_watchers = list(self.screen._cb_watchers)
        self.original_alternate = self.screen._alternate

        self.screen._cb_watchers = []
        self.screen._resize_timer = None

        self.addCleanup(self._restore_screen_state)

    def _restore_screen_state(self) -> None:
        self.screen._cursor = self.original_cursor
        self.screen._dimension = self.original_dimension
        self.screen._resize_timer = self.original_resize_timer
        self.screen._cb_watchers = self.original_watchers
        self.screen._alternate = self.original_alternate


class TestScreenResizeWatcher(ScreenTestCase):
    def test_resize_watcher_should_invoke_registered_callbacks(self) -> None:
        callback = MagicMock()
        initial_dimension = (24, 80)
        new_dimension = (42, 120)

        self.screen._dimension = initial_dimension

        fake_thread = MagicMock()
        fake_thread.is_alive.return_value = True

        timer_instances = []

        class FakeTimer:
            def __init__(self, interval, function):
                self.interval = interval
                self.function = function
                self.started = False
                timer_instances.append(self)

            def start(self):
                self.started = True

        with patch("clitt.core.term.screen.threading.main_thread", return_value=fake_thread), \
            patch("clitt.core.term.screen.Timer", new=lambda interval, func: FakeTimer(interval, func)), \
            patch("clitt.core.term.screen.get_dimensions", side_effect=[initial_dimension, new_dimension]) as mock_dimensions:

            self.screen.add_watcher(callback)

            self.assertEqual(1, len(timer_instances))
            self.assertEqual(self.screen.RESIZE_WATCH_INTERVAL, timer_instances[0].interval)
            self.assertTrue(timer_instances[0].started)
            callback.assert_not_called()

            timer_instances[0].function()

            self.assertEqual(2, len(timer_instances))
            self.assertEqual(2, mock_dimensions.call_count)
            callback.assert_called_once_with()

        self.assertEqual(new_dimension, self.screen._dimension)


class TestScreenAlternate(ScreenTestCase):
    def test_alternate_setter_should_emit_escape_and_track_cursor(self) -> None:
        fake_cursor = MagicMock()
        fake_cursor.track = MagicMock()
        self.screen._cursor = fake_cursor
        self.screen._alternate = False

        with patch("clitt.core.term.screen.sysout") as mock_sysout:
            self.screen.alternate = True

            mock_sysout.assert_called_once_with("%SCA%", end="")
            fake_cursor.track.assert_called_once_with()
            self.assertTrue(self.screen._alternate)

            mock_sysout.reset_mock()
            fake_cursor.track.reset_mock()

            self.screen.alternate = True

            mock_sysout.assert_not_called()
            fake_cursor.track.assert_not_called()

            self.screen.alternate = False

            mock_sysout.assert_called_once_with("%SCM%", end="")
            fake_cursor.track.assert_called_once_with()
            self.assertFalse(self.screen._alternate)


class TestScreenClear(ScreenTestCase):
    def test_clear_should_home_and_erase_screen(self) -> None:
        fake_cursor = MagicMock()
        self.screen._cursor = fake_cursor

        self.screen.clear()

        fake_cursor.home.assert_called_once_with()
        fake_cursor.erase.assert_called_once_with(Portion.SCREEN)


if __name__ == "__main__":
    unittest.main()
