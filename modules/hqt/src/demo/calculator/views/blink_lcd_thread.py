#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Hqt
@package: demo.qtdemos.calculator.views
   @file: blink_lcd_thread.py
@created: Wed, 30 Jun 2021
 @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: https://github.com/yorevs/hspylib
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QLCDNumber
from threading import Thread
from time import sleep


class BlinkLcdThread(Thread):
    def __init__(self, lcd: QLCDNumber, delay: float):
        Thread.__init__(self)
        self._lcd = lcd
        self._delay = delay

    def run(self):
        palette = self._lcd.palette()
        fg_color = palette.color(QPalette.ColorRole.WindowText)
        bg_color = palette.color(QPalette.ColorRole.Window)
        palette.setColor(QPalette.ColorRole.WindowText, bg_color)
        self._lcd.setPalette(palette)
        sleep(self._delay)
        palette.setColor(QPalette.ColorRole.WindowText, fg_color)
        self._lcd.setPalette(palette)
