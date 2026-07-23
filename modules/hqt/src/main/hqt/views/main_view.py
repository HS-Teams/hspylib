#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Hqt
@package: hqt.views
   @file: main_view.py
@created: Tue, 4 May 2021
 @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: https://github.com/yorevs/hspylib
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from abc import abstractmethod
from hqt.views.qt_view import QtView
from PyQt6 import uic


class MainView(QtView):
    """TODO"""

    def __init__(self, ui_file_path: str):
        form_class, window_class = uic.loadUiType(ui_file_path)
        self.window, self.ui = window_class(), form_class()
        self.ui.setupUi(self.window)
        self.form = self.ui
        self.parent = None
        self._setup_ui()

    @abstractmethod
    def _setup_ui(self) -> None:
        """TODO"""

    def show(self) -> None:
        """TODO"""
        self.window.show()
