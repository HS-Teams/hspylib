#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Typed schema field used by the dynamic form builder."""

from __future__ import annotations

from abc import ABC
from copy import deepcopy
from typing import Any, Callable, Optional, Union

from kafman.core.schema.avro.avro_type import AvroType
from kafman.core.schema.json.json_type import JsonType
from kafman.core.schema.widget_utils import (
    FieldEditor,
    InputValue,
    MISSING,
    WidgetUtils,
)
from PyQt6.QtWidgets import QWidget


class SchemaField(ABC):
    def __init__(
        self,
        name: str,
        doc: str,
        a_type: Union[AvroType, JsonType],
        default: Any = MISSING,
        required: bool = True,
        *,
        nullable: bool = False,
        constraints: Optional[dict[str, Any]] = None,
        item_type: Any = None,
    ):
        self.name = name
        self.doc = doc
        self.a_type = a_type
        self.default = default
        self.required = required
        self.nullable = nullable
        self.constraints = constraints or {}
        self.item_type = item_type
        self.symbols: list[Any] = []
        self.widget: Optional[FieldEditor] = None
        self.nested_value: dict[str, Any] = {}
        self._value_provider: Optional[Callable[[], InputValue]] = None
        self.apply_default(default)

    def apply_default(self, default: Any) -> None:
        """Apply a schema default before the field's input widget is created."""
        self.default = default
        if isinstance(default, dict):
            self.nested_value = deepcopy(default)

    def __str__(self) -> str:
        return (
            f"name={self.name}, type={self.a_type}, required={self.required}, "
            f"nullable={self.nullable}, default={self.default!r}"
        )

    def create_input_widget(self) -> QWidget:
        self.widget = WidgetUtils.create_editor(
            self.a_type.value,
            doc=self.doc,
            symbols=self.symbols,
            default=self.default,
            nullable=self.nullable,
            optional=not self.required,
            constraints=self.constraints,
        )
        return self.widget

    def wrap_nested_widget(self, widget: QWidget) -> QWidget:
        self.widget = FieldEditor(
            widget,
            nullable=self.nullable,
            optional=not self.required,
            default=self.default,
        )
        return self.widget

    def set_value_provider(self, provider: Callable[[], InputValue]) -> None:
        """Use a nested form or composite editor as this field's value source."""
        self._value_provider = provider

    def value(self) -> InputValue:
        if self.widget is None:
            return MISSING
        if self.widget.mode() == FieldEditor.OMIT:
            return MISSING
        if self.widget.mode() == FieldEditor.NULL:
            return None
        if self._value_provider is not None:
            return self._value_provider()
        if self.a_type.value in {"record", "object"}:
            return self.nested_value
        return WidgetUtils.editor_value(
            self.widget, self.a_type.value, item_type=self.item_type
        )
