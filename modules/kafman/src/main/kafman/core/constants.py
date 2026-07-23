#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Kafman
@package: kafman.core
   @file: constants.py
@created: Wed, 30 Jun 2021
 @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: https://github.com/yorevs/hspylib
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from abc import ABC
from PyQt6.QtGui import QColor

MAX_HISTORY_SIZE_BYTES = 1024 * 1024


# pylint: disable=too-few-public-methods
class StatusColor(ABC):
    """Colors to be used in the status text"""

    white = QColor("#FFFFFF")
    red = QColor("#FF554D")
    green = QColor("#28C941")
    yellow = QColor("#FEBE2F")
    blue = QColor("#2380FA")
    orange = QColor("#FF8C36")
    purple = QColor("#D9A2FF")
