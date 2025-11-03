#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
   @project: HsPyLib
   test.tools
      @file: test_commons.py
   @created: Thu, 03 Nov 2022
    @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
      @site: https://github.com/yorevs/hspylib
   @license: MIT - Please refer to <https://opensource.org/licenses/MIT>

   Copyright·(c)·2024,·HSPyLib
"""
from hspylib.core.tools.commons import class_attribute_names, syserr, sysout, to_bool

from contextlib import redirect_stderr, redirect_stdout
import io
import os
import sys
import unittest


class TestCommons(unittest.TestCase):
    def test_should_retrieve_class_attribute_names_without_instantiation(self) -> None:
        class Dummy:
            def __init__(self, foo: int = 1, bar: str = "baz"):
                self.foo = foo
                self.bar = bar

        class RequiresArgs:
            def __init__(self, foo: int, bar: str):  # pragma: no cover - defensive guard
                raise AssertionError("Instantiation should not occur")

        self.assertEqual(("foo", "bar"), class_attribute_names(Dummy))
        self.assertEqual(("foo", "bar"), class_attribute_names(RequiresArgs))
        self.assertIsNone(class_attribute_names(None))

    def test_should_return_proper_bool_value(self) -> None:
        self.assertFalse(to_bool(""))
        self.assertFalse(to_bool("0"))
        self.assertFalse(to_bool("off"))
        self.assertFalse(to_bool("no"))
        self.assertTrue(to_bool("1"))
        self.assertTrue(to_bool("true"))
        self.assertTrue(to_bool("True"))
        self.assertTrue(to_bool("on"))
        self.assertTrue(to_bool("yes"))

        self.assertFalse(to_bool("good"))
        self.assertTrue(to_bool("good", {"good"}))
        self.assertFalse(to_bool("bad", {"good"}))

    def test_shouldNotFailIfReceivedNoneValueToSysoutOrSyserr(self) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        try:
            with redirect_stdout(stdout_buffer):
                print("")
                print("")
            with redirect_stderr(stderr_buffer):
                print("", file=sys.stderr)
                print("", file=sys.stderr)
        except TypeError as err:
            self.fail(f"sysout/syserr raised TypeError unexpectedly => {err}")

        expected_output = os.linesep * 2
        self.assertEqual(expected_output, stdout_buffer.getvalue())
        self.assertEqual(expected_output, stderr_buffer.getvalue())


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCommons)
    unittest.TextTestRunner(verbosity=2, failfast=True, stream=sys.stdout).run(suite)
