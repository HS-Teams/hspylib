#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
   @project: hspylib
   @package: hspylib.test.core
      @file: test_object_mapper.py
   @created: Tue, 11 Jun 2024
   @author: "<B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
      @site: "https://github.com/yorevs/hspylib")
   @license: MIT - Please refer to <https://opensource.org/licenses/MIT>

   Copyright·(c)·2024,·HSPyLib
"""

from hspylib.core.object_mapper import ObjectMapper

import sys
import unittest


class SourceType:
    def __init__(self) -> None:
        self.name = "Alice"
        self.age = 30
        self.extra = "ignored"


class TargetType:
    def __init__(self, name: str, age: int) -> None:
        self.name = name
        self.age = age
        self.initialized = True


class TestObjectMapper(unittest.TestCase):
    def test_should_convert_using_target_init_signature(self) -> None:
        source = SourceType()

        result = ObjectMapper().convert(source, TargetType)

        self.assertIsInstance(result, TargetType)
        self.assertEqual(source.name, result.name)
        self.assertEqual(source.age, result.age)
        self.assertTrue(result.initialized)
        self.assertFalse(hasattr(result, "extra"))


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestObjectMapper)
    unittest.TextTestRunner(verbosity=2, failfast=True, stream=sys.stdout).run(suite)
