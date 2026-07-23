#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Hqt
@package: hqt.promotions
   @file: hframe.py
@created: Tue, 4 May 2021
 @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: https://github.com/yorevs/hspylib
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QFrame
from typing import Optional


class HFrame(QFrame):
    """TODO"""

    keyPressed = pyqtSignal(int)

    def keyPressEvent(self, event: Optional[QKeyEvent]) -> None:
        """TODO"""
        if event is not None:
            self.keyPressed.emit(int(event.key()))
        super().keyPressEvent(event)
