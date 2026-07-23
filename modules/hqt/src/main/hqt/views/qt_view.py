#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Hqt
@package: hqt.views
   @file: qt_view.py
@created: Tue, 4 May 2021
 @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: https://github.com/yorevs/hspylib
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from abc import ABC
from hspylib.core.preconditions import check_argument, check_state
from hspylib.core.tools.commons import root_dir
from PyQt6 import uic
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QWidget
from typing import Optional, Tuple, Type

import os


class QtView(ABC):
    """TODO"""

    MAIN_QT_VIEW_UI = "main_qt_view.ui"

    @staticmethod
    def load_form(form_file: str, load_dir: Optional[str]) -> Tuple[Type, Type]:
        """Load the ui form from the .ui file"""

        form_dir = load_dir if load_dir else f"{root_dir()}/resources/forms/"
        check_argument(
            os.path.exists(form_dir) and os.path.isdir(form_dir),
            "Load dir {} does not exist or is not a folder",
            form_dir,
        )
        filepath = f"{form_dir}/{form_file}"
        check_state(
            os.path.exists(filepath)
            and os.path.isfile(filepath)
            and filepath.lower().endswith(".ui"),
            "Form file {} does not exist or it is not a valid UI form file",
            form_file,
        )

        return uic.loadUiType(filepath)

    def __init__(
        self,
        ui_file: str = MAIN_QT_VIEW_UI,
        load_dir: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ):
        ui_clazz, window_clazz = self.load_form(ui_file, load_dir)
        # Must come after the initialization above
        check_state(
            ui_clazz is not None and window_clazz is not None,
            "Unable to initialize UI and Window objects",
        )
        self.window, self.ui = window_clazz(), ui_clazz()
        self.ui.setupUi(self.window)
        self.parent = parent

    def show(self) -> None:
        """Show the main widget"""
        self.window.show()

    def set_default_font(self, default_font: QFont = QFont("Courier New", 14)):
        """Set font for all UI components at once"""
        widgets = list(
            filter(lambda o: hasattr(getattr(self.ui, o), "setFont"), vars(self.ui))
        )
        list(map(lambda w: getattr(self.ui, w).setFont(default_font), widgets))
