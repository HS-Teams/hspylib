# _*_ coding: utf-8 _*_
#
# hspylib v1.12.54
#
# Package: test
"""Package initialization."""

from pathlib import Path
import sys

_TEST_PACKAGE = Path(__file__).resolve().parent
_SRC_ROOT = _TEST_PACKAGE.parent
_MAIN_SRC = _SRC_ROOT / "main"

for path in (_SRC_ROOT, _MAIN_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

__all__ = [
    'core',
    'mock',
    'modules',
    'shared'
]
__version__ = '1.12.54'
