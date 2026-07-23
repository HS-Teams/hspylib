#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Kafman
@package: kafman.views.promotions
   @file: form_pane.py
@created: Wed, 8 Jun 2022
 @author: "<B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: "https://github.com/yorevs/hspylib")
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from clitt.core.icons.font_awesome.form_icons import FormIcons
from hqt.promotions.hframe import HFrame
from hqt.promotions.hstacked_widget import HStackedWidget
from hspylib.core.preconditions import check_argument, check_not_none
from kafman.core.schema.schema_field import SchemaField
from kafman.core.schema.widget_utils import InputWidget, MISSING, WidgetUtils
from kafman.views.promotions.form_area import FormArea
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from typing import Any, Optional


class FormPane(HFrame):
    """TODO"""

    LABEL_COLUMN = 0

    REQUIRED_COLUMN = 1

    FIELD_COLUMN = 2

    def __init__(
        self, parent: QWidget, parent_form: Optional["FormPane"], form_name: str
    ):
        super().__init__(parent)
        check_argument(
            form_name is not None and len(form_name) > 1,
            f"Invalid form name: {form_name}",
        )
        self._fields: dict[str, Any] = {}
        self._schema_fields: dict[str, SchemaField] = {}
        self._name = form_name
        self._parent_form = parent_form
        self._form_frame = QFrame(self)
        self._form_area = FormArea(self)
        self._box = QVBoxLayout(self)
        self._grid = QGridLayout(self._form_frame)

        self.setObjectName(form_name)
        self.setContentsMargins(0, 0, 0, 0)
        self.setFrameStyle(int(QFrame.Shape.StyledPanel) | int(QFrame.Shadow.Raised))
        self._box.addWidget(self._form_area)
        self._form_frame.setFrameStyle(int(QFrame.Shape.NoFrame))
        self._form_frame.setContentsMargins(0, 0, 0, 0)
        self._form_area.setWidget(self._form_frame)

    def grid(self) -> QGridLayout:
        return self._grid

    def name(self) -> str:
        return self._name

    def parent_name(self) -> Optional[str]:
        return self._parent_form.name() if self._parent_form else None

    def parent_form(self) -> Optional["FormPane"]:
        return self._parent_form

    def schema_field(self, field_name: str) -> Optional[SchemaField]:
        return self._schema_fields.get(field_name)

    def add_field(
        self,
        field_name: str,
        label: QLabel,
        req_label: QLabel,
        widget: InputWidget,
        row: int,
        field: Optional[SchemaField] = None,
    ) -> None:
        """TODO"""

        check_not_none(widget)
        widget.setObjectName(field_name)
        self._grid.addWidget(label, row, self.LABEL_COLUMN)
        self._grid.addWidget(req_label, row, self.REQUIRED_COLUMN)
        self._grid.addWidget(widget, row, self.FIELD_COLUMN)
        if field is not None:
            self._schema_fields[field_name] = field
            self._fields[field_name] = MISSING

    def add_form_button(
        self,
        field_name: str,
        label: QLabel,
        req_label: QLabel,
        row: int,
        index: int,
        form_stack: HStackedWidget,
        field: SchemaField,
    ) -> None:
        """TODO"""

        fill_button = QPushButton(FormIcons.ARROW_RIGHT.value + " Fill")
        fill_button.clicked.connect(lambda: form_stack.slide_to_index(index))
        WidgetUtils.setup_widget_commons(fill_button, "Click to fill the form")
        fill_button.setMaximumWidth(100)
        fill_button.setMinimumHeight(30)
        fill_button.setDefault(False)
        fill_button.setAutoDefault(False)
        editor = field.wrap_nested_widget(fill_button)
        self.add_field(field_name, label, req_label, editor, row, field)

    def add_back_button(self, back_index: int, form_stack: HStackedWidget) -> None:
        """TODO"""

        row = self._grid.rowCount() + 1
        back_button = QPushButton(FormIcons.ARROW_LEFT.value + " Back")
        back_button.clicked.connect(lambda: form_stack.slide_to_index(back_index))
        WidgetUtils.setup_widget_commons(back_button, "Click to go to previous form")
        back_button.setMaximumWidth(100)
        back_button.setMinimumHeight(30)
        back_button.setDefault(False)
        back_button.setAutoDefault(False)
        self._grid.addWidget(back_button, row, self.LABEL_COLUMN)

    def fields(self) -> dict:
        """TODO"""

        for field_name, field in self._schema_fields.items():
            self._fields[field_name] = field.value()

        return self._fields
