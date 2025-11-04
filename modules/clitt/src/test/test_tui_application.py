#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for the TUIApplication cleanup routine."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

from _test_setup import setup_test_environment

setup_test_environment()

from clitt.core.tui.tui_application import TUIApplication
from hspylib.core.metaclass.singleton import Singleton
from hspylib.modules.application.exit_status import ExitStatus


class _TestTUIApplication(TUIApplication):
    """Minimal concrete implementation for testing."""

    def _setup_arguments(self) -> None:  # pragma: no cover - not needed for tests
        pass

    def _main(self, *params, **kwargs) -> ExitStatus:  # pragma: no cover - not needed for tests
        return ExitStatus.SUCCESS


class TestTUIApplicationCleanup(unittest.TestCase):
    """Verify that TUIApplication properly restores the terminal state."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _TestTUIApplication("TestApp")

    @classmethod
    def tearDownClass(cls) -> None:
        if Singleton.has_instance(_TestTUIApplication):
            Singleton.del_instance(_TestTUIApplication)

    def test_cleanup_should_toggle_alternate_on_success(self) -> None:
        """Successful exits should disable the alternate screen."""

        with patch("clitt.core.tui.tui_application.terminal.restore") as mock_restore:
            mock_screen = MagicMock()
            mock_screen.alternate = True

            with patch("clitt.core.tui.tui_application.screen", mock_screen):
                type(self).app._exit_code = ExitStatus.SUCCESS
                type(self).app._cleanup()

        mock_restore.assert_called_once_with()
        self.assertFalse(mock_screen.alternate)

    def test_cleanup_should_not_toggle_alternate_on_failure(self) -> None:
        """Non-success exits must leave the alternate screen untouched."""

        with patch("clitt.core.tui.tui_application.terminal.restore") as mock_restore:
            mock_screen = MagicMock()
            mock_screen.alternate = True

            with patch("clitt.core.tui.tui_application.screen", mock_screen):
                type(self).app._exit_code = ExitStatus.ABNORMAL
                type(self).app._cleanup()

        mock_restore.assert_called_once_with()
        self.assertTrue(mock_screen.alternate)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
