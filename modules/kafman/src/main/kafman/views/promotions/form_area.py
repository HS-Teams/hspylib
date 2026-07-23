#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Kafman
@package: kafman.views.promotions
   @file: form_area.py
@created: Wed, 8 Jun 2022
 @author: "<B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: "https://github.com/yorevs/hspylib")
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from hqt.promotions.hstacked_widget import HStackedWidget
from hspylib.core.preconditions import check_argument
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QAbstractScrollArea, QFrame, QScrollArea, QWidget
from typing import TYPE_CHECKING, Optional, cast

import json

if TYPE_CHECKING:
    from kafman.views.promotions.form_pane import FormPane


class FormArea(QScrollArea):
    """TODO"""

    keyPressed = pyqtSignal(int)

    def __init__(self, parent: Optional[QWidget]):
        super().__init__(parent)
        self._form: Optional[QWidget] = None
        self.setWidgetResizable(True)
        self.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.setFrameStyle(int(QFrame.Shape.NoFrame) | int(QFrame.Shadow.Plain))

    def setWidget(self, widget: Optional[QWidget]) -> None:
        if self._form is not None:
            check_argument(
                isinstance(widget, HStackedWidget),
                "Only HStackedWidget type instances are accepted",
            )
        super().setWidget(widget)
        self._form = widget
        self.horizontalScrollBar().setValue(0)
        self.verticalScrollBar().setValue(0)

    def get_form(self) -> Optional[QWidget]:
        """TODO"""
        return self._form

    def values(self) -> str:
        """TODO"""

        form = self._form
        check_argument(
            isinstance(form, HStackedWidget), "A form stack has not been assigned"
        )
        assert isinstance(form, HStackedWidget)
        root = {}
        for widget in form.widgets():
            pane = cast("FormPane", widget)
            if pane.parent_form() is None:
                root.update(pane.values())
                break

        return json.dumps(root, indent=2)
