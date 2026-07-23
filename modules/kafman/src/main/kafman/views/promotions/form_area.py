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
from kafman.core.schema.widget_utils import InputValue, MISSING
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QAbstractScrollArea, QFrame, QScrollArea, QWidget
from typing import TYPE_CHECKING, Optional, Union, cast

import json

if TYPE_CHECKING:
    from kafman.views.promotions.form_pane import FormPane


class FormArea(QScrollArea):
    """TODO"""

    keyPressed = pyqtSignal(int)

    @staticmethod
    def _is_not_empty(value: Union[InputValue, dict]) -> bool:
        return value is not MISSING

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
            fields = {k: v for k, v in pane.fields().items() if self._is_not_empty(v)}
            parent = pane.parent_form()
            if parent is None:
                root.update(fields)
            else:
                parent_field = parent.schema_field(pane.name())
                if parent_field is None:
                    continue
                parent_value = parent_field.value()
                if parent_value is MISSING or parent_value is None:
                    continue
                parent_field.nested_value.update(fields)

        return json.dumps(root, indent=2)
