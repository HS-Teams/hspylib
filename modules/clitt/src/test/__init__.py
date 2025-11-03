# _*_ coding: utf-8 _*_
#
# hspylib-clitt v0.9.145
#
# Package: test
"""Package initialization."""

from ._test_setup import setup_test_environment


setup_test_environment()

__all__ = ["test_line_input", "test_terminal"]
__version__ = "0.9.145"
