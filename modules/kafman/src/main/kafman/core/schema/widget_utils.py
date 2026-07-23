#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Schema-aware Qt widget creation and value conversion."""

from __future__ import annotations

import base64
import json
from abc import ABC
from typing import Any, Iterable, Optional, TypeAlias

from hqt.promotions.hcombobox import HComboBox
from hqt.promotions.hlistwidget import HListWidget
from hspylib.core.exception.exceptions import InvalidStateError
from PyQt6.QtCore import QRegularExpression, Qt
from PyQt6.QtGui import QFont, QRegularExpressionValidator
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSizePolicy,
    QSpinBox,
    QWidget,
)


class _MissingValue:
    def __repr__(self) -> str:
        return "MISSING"


MISSING = _MissingValue()
InputValue: TypeAlias = Any
InputWidget: TypeAlias = QWidget
WidgetType: TypeAlias = type[QWidget]


class FieldEditor(QWidget):
    """Wrap an input widget with explicit value/null/omit state."""

    VALUE = "value"
    NULL = "null"
    OMIT = "omit"

    def __init__(
        self,
        input_widget: Optional[QWidget],
        *,
        nullable: bool = False,
        optional: bool = False,
        default: Any = MISSING,
    ):
        super().__init__()
        self.input_widget = input_widget
        self._mode = QComboBox(self)
        self._mode.addItem("Value", self.VALUE)
        if nullable:
            self._mode.addItem("Null", self.NULL)
        if optional:
            self._mode.addItem("Omit", self.OMIT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if self._mode.count() > 1:
            self._mode.setMaximumWidth(90)
            layout.addWidget(self._mode)
        if input_widget is not None:
            layout.addWidget(input_widget)
        else:
            layout.addWidget(QLabel("null", self))

        if default is MISSING:
            initial_mode = (
                self.OMIT if optional else self.NULL if nullable else self.VALUE
            )
        elif default is None and nullable:
            initial_mode = self.NULL
        else:
            initial_mode = self.VALUE
        index = self._mode.findData(initial_mode)
        self._mode.setCurrentIndex(max(0, index))
        self._mode.currentIndexChanged.connect(self._sync_enabled)
        self._sync_enabled()

    def mode(self) -> str:
        return str(self._mode.currentData())

    def set_mode(self, mode: str) -> None:
        index = self._mode.findData(mode)
        if index >= 0:
            self._mode.setCurrentIndex(index)

    def _sync_enabled(self) -> None:
        if self.input_widget is not None:
            self.input_widget.setEnabled(self.mode() == self.VALUE)


class WidgetUtils(ABC):
    QWIDGET_TYPE_MAP: dict[str, Optional[WidgetType]] = {
        "null": None,
        "boolean": QCheckBox,
        "integer": QSpinBox,
        "int": QSpinBox,
        "long": QLineEdit,
        "float": QDoubleSpinBox,
        "double": QDoubleSpinBox,
        "number": QDoubleSpinBox,
        "bytes": QLineEdit,
        "string": QLineEdit,
        "fixed": QLineEdit,
        "enum": HComboBox,
        "array": HListWidget,
        "map": QPlainTextEdit,
        "union": QPlainTextEdit,
        "record": QPlainTextEdit,
        "object": QPlainTextEdit,
    }

    @classmethod
    def get_widget_type(cls, field_type: str) -> Optional[WidgetType]:
        if field_type not in cls.QWIDGET_TYPE_MAP:
            raise InvalidStateError(f'Field type "{field_type}" is not supported')
        return cls.QWIDGET_TYPE_MAP[field_type]

    @classmethod
    def create_editor(
        cls,
        field_type: str,
        *,
        doc: Optional[str] = None,
        symbols: Optional[Iterable[Any]] = None,
        default: Any = MISSING,
        nullable: bool = False,
        optional: bool = False,
        constraints: Optional[dict[str, Any]] = None,
    ) -> FieldEditor:
        widget_type = cls.get_widget_type(field_type)
        input_widget = widget_type() if widget_type is not None else None
        if input_widget is not None:
            cls.setup_widget(
                input_widget,
                field_type,
                doc=doc,
                symbols=symbols,
                default=default,
                constraints=constraints,
            )
        editor = FieldEditor(
            input_widget, nullable=nullable, optional=optional, default=default
        )
        editor.setToolTip(doc or "")
        editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return editor

    @classmethod
    def setup_widget(
        cls,
        widget: QWidget,
        field_type: str,
        *,
        doc: Optional[str] = None,
        symbols: Optional[Iterable[Any]] = None,
        default: Any = MISSING,
        constraints: Optional[dict[str, Any]] = None,
    ) -> QWidget:
        constraints = constraints or {}
        actual_default = None if default is MISSING else default
        if isinstance(widget, HComboBox):
            cls.setup_combo_box(widget, symbols, doc, actual_default)
        elif isinstance(widget, HListWidget):
            cls.setup_list(
                widget,
                doc,
                actual_default if isinstance(actual_default, list) else None,
            )
        elif isinstance(widget, QCheckBox):
            cls.setup_checkbox(widget, doc, actual_default)
        elif isinstance(widget, QSpinBox):
            cls.setup_spin_box(widget, doc, actual_default, constraints)
        elif isinstance(widget, QDoubleSpinBox):
            cls.setup_double_spin_box(widget, doc, actual_default, constraints)
        elif isinstance(widget, QLineEdit):
            cls.setup_line_edit(widget, doc, actual_default, constraints)
        elif isinstance(widget, QPlainTextEdit):
            cls.setup_json_editor(widget, doc, actual_default, field_type)
        else:
            raise InvalidStateError(
                f'Widget type "{type(widget).__name__}" is not supported'
            )
        return widget

    @staticmethod
    def setup_widget_commons(widget: QWidget, tooltip: Optional[str]) -> QWidget:
        widget.setToolTip(tooltip or "")
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        widget.setStyleSheet("QWidget {padding: 5px;}")
        widget.setFont(QFont("DroidSansMono Nerd Font", 14))
        widget.setMinimumHeight(35)
        return widget

    @staticmethod
    def setup_combo_box(
        widget: HComboBox,
        symbols: Optional[Iterable[Any]],
        tooltip: Optional[str] = None,
        default: Any = None,
    ) -> QWidget:
        for symbol in symbols or []:
            widget.addItem(str(symbol), symbol)
        widget.setEditable(False)
        if default is not None:
            index = widget.findData(default)
            widget.setCurrentIndex(index if index >= 0 else 0)
        return WidgetUtils.setup_widget_commons(widget, tooltip)

    @staticmethod
    def setup_list(
        widget: HListWidget,
        tooltip: Optional[str] = None,
        all_items: Optional[Iterable[Any]] = None,
    ) -> QWidget:
        for item in all_items or []:
            widget.set_item(
                json.dumps(item) if isinstance(item, (dict, list)) else str(item)
            )
        widget.set_editable()
        widget.set_selectable()
        widget.set_context_menu_enable()
        return WidgetUtils.setup_widget_commons(widget, tooltip)

    @staticmethod
    def setup_checkbox(
        widget: QCheckBox, tooltip: Optional[str] = None, default: Any = False
    ) -> QWidget:
        widget.setChecked(bool(default) if default is not None else False)
        return WidgetUtils.setup_widget_commons(widget, tooltip)

    @staticmethod
    def setup_spin_box(
        widget: QSpinBox,
        tooltip: Optional[str] = None,
        default: Any = 0,
        constraints: Optional[dict[str, Any]] = None,
    ) -> QWidget:
        constraints = constraints or {}
        minimum = int(
            constraints.get("minimum", constraints.get("exclusiveMinimum", -(2**31)))
        )
        maximum = int(
            constraints.get("maximum", constraints.get("exclusiveMaximum", 2**31 - 1))
        )
        if "exclusiveMinimum" in constraints:
            minimum += 1
        if "exclusiveMaximum" in constraints:
            maximum -= 1
        widget.setRange(minimum, maximum)
        widget.setValue(int(default) if default is not None else max(0, minimum))
        widget.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        return WidgetUtils.setup_widget_commons(widget, tooltip)

    @staticmethod
    def setup_double_spin_box(
        widget: QDoubleSpinBox,
        tooltip: Optional[str] = None,
        default: Any = 0.0,
        constraints: Optional[dict[str, Any]] = None,
    ) -> QWidget:
        constraints = constraints or {}
        minimum = float(
            constraints.get("minimum", constraints.get("exclusiveMinimum", -1e100))
        )
        maximum = float(
            constraints.get("maximum", constraints.get("exclusiveMaximum", 1e100))
        )
        widget.setRange(minimum, maximum)
        widget.setDecimals(8)
        widget.setValue(
            float(default) if default is not None else min(max(0.0, minimum), maximum)
        )
        widget.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        return WidgetUtils.setup_widget_commons(widget, tooltip)

    @staticmethod
    def setup_line_edit(
        widget: QLineEdit,
        tooltip: Optional[str] = None,
        default: Any = "",
        constraints: Optional[dict[str, Any]] = None,
    ) -> QWidget:
        constraints = constraints or {}
        widget.setPlaceholderText(tooltip or "")
        if "maxLength" in constraints:
            widget.setMaxLength(int(constraints["maxLength"]))
        if pattern := constraints.get("pattern"):
            widget.setValidator(
                QRegularExpressionValidator(QRegularExpression(str(pattern)), widget)
            )
        if isinstance(default, bytes):
            widget.setText(f"base64:{base64.b64encode(default).decode('ascii')}")
        else:
            widget.setText("" if default is None else str(default))
        return WidgetUtils.setup_widget_commons(widget, tooltip)

    @staticmethod
    def setup_json_editor(
        widget: QPlainTextEdit,
        tooltip: Optional[str] = None,
        default: Any = None,
        field_type: str = "object",
    ) -> QWidget:
        if default is None:
            default = {} if field_type in {"map", "record", "object"} else None
        widget.setPlaceholderText(tooltip or "Enter valid JSON")
        widget.setPlainText("" if default is None else json.dumps(default, indent=2))
        widget.setMinimumHeight(90)
        return WidgetUtils.setup_widget_commons(widget, tooltip)

    @classmethod
    def editor_value(
        cls,
        editor: FieldEditor,
        field_type: str,
        *,
        item_type: Any = None,
    ) -> InputValue:
        if editor.mode() == FieldEditor.OMIT:
            return MISSING
        if editor.mode() == FieldEditor.NULL:
            return None
        widget = editor.input_widget
        if widget is None:
            return None
        if isinstance(widget, HComboBox):
            data = widget.currentData()
            return widget.currentText() if data is None else data
        if isinstance(widget, HListWidget):
            return [cls.coerce_value(value, item_type) for value in widget.as_list()]
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            return widget.value()
        if isinstance(widget, QLineEdit):
            return cls.coerce_value(widget.text(), field_type)
        if isinstance(widget, QPlainTextEdit):
            text = widget.toPlainText().strip()
            return None if not text else json.loads(text)
        raise InvalidStateError(
            f'Widget type "{type(widget).__name__}" is not supported'
        )

    @staticmethod
    def coerce_value(value: Any, field_type: Any) -> Any:
        type_name = getattr(field_type, "value", field_type)
        if isinstance(type_name, dict):
            type_name = type_name.get("type")
        if type_name in {"int", "long", "integer"}:
            return int(value)
        if type_name in {"float", "double", "number"}:
            return float(value)
        if type_name in {"boolean", "bool"}:
            return (
                value
                if isinstance(value, bool)
                else str(value).lower() in {"true", "1", "yes"}
            )
        if type_name in {"object", "record", "map", "array", "union"} and isinstance(
            value, str
        ):
            return json.loads(value)
        return value
