#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
   @project: HsPyLib
   test.core.exception
      @file: test_exceptions.py
   @created: Fri, 10 May 2024
   @license: MIT - Please refer to <https://opensource.org/licenses/MIT>
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

TEST_ROOT = Path(__file__).resolve().parents[3]
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))
SRC_MAIN = TEST_ROOT / "main"
if str(SRC_MAIN) not in sys.path:
    sys.path.insert(0, str(SRC_MAIN))

from hspylib.core.exception.exceptions import (
    ApplicationError,
    HSBaseException,
    InvalidArgumentError,
    InvalidInputError,
    InvalidJsonMapping,
    InvalidMapping,
    InvalidOptionError,
    InvalidStateError,
    KeyboardInputError,
    PropertyError,
    WidgetExecutionError,
    WidgetNotFoundError,
)


class TestHsBaseException(unittest.TestCase):
    def test_should_format_message_with_cause_and_context(self) -> None:
        with patch("hspylib.core.exception.exceptions.log.error") as mock_log:
            try:
                raise ValueError("bad value")
            except ValueError as err:
                exc = HSBaseException("Something happened", err)

        message = str(exc)
        self.assertTrue(message.startswith("### Something happened :bad value:"))
        self.assertRegex(message, r"\(File .*test_exceptions.py, Line ")
        mock_log.assert_called_once_with(message)

    def test_should_preserve_message_when_no_active_exception(self) -> None:
        with patch("hspylib.core.exception.exceptions.log.error") as mock_log:
            exc = HSBaseException("Just a message")

        self.assertEqual("Just a message", str(exc))
        mock_log.assert_called_once_with("Just a message")

    def test_custom_exceptions_should_preserve_hierarchy(self) -> None:
        expected_subclasses = [
            ApplicationError,
            PropertyError,
            KeyboardInputError,
            InvalidOptionError,
            WidgetExecutionError,
            WidgetNotFoundError,
            InvalidMapping,
            InvalidJsonMapping,
        ]
        for subclass in expected_subclasses:
            with self.subTest(subclass=subclass.__name__):
                self.assertTrue(issubclass(subclass, HSBaseException))

        direct_exceptions = [InvalidInputError, InvalidArgumentError, InvalidStateError]
        for exc_type in direct_exceptions:
            with self.subTest(exc_type=exc_type.__name__):
                self.assertTrue(issubclass(exc_type, Exception))
                self.assertFalse(issubclass(exc_type, HSBaseException))


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestHsBaseException)
    unittest.TextTestRunner(verbosity=2, failfast=True).run(suite)
