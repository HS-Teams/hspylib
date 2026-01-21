#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
   @project: HsPyLib
   @package: clitt.core.tui.minput
      @file: field_builder.py
   @created: Thu, 20 May 2021
    @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
      @site: https://github.com/yorevs/hspylib
   @license: MIT - Please refer to <https://opensource.org/licenses/MIT>

   Copyright·(c)·2024,·HSPyLib
"""
from clitt.core.tui.minput.access_type import AccessType
from clitt.core.tui.minput.form_field import FieldValidator_Fn, FormField
from clitt.core.tui.minput.input_type import InputType
from clitt.core.tui.minput.input_validator import InputValidator
from clitt.core.tui.minput.minput_utils import get_selected, MASK_SYMBOLS, unpack_masked, VALUE_SEPARATORS
from functools import reduce
from hspylib.core.preconditions import check_argument
from hspylib.core.tools.commons import to_bool
from hspylib.core.tools.text_tools import snakecase
from operator import add
from typing import Any

import re


class FieldBuilder:
    """MenuInput form field builder."""

    @staticmethod
    def _validate_field(field: FormField) -> bool:
        match field.itype:
            case InputType.MASKED:
                value, mask = unpack_masked(field.value)
                valid = reduce(add, list(map(mask[len(value) :].count, MASK_SYMBOLS))) == 0
            case InputType.CHECKBOX:
                valid = isinstance(field.value, bool)
            case InputType.SELECT:
                _, value = get_selected(field.value)
                length = len(str(value or ""))
                valid = field.min_length <= length <= field.max_length
            case _:
                length = len(str(field.value or ""))
                valid = field.min_length <= length <= field.max_length
        return valid

    def __init__(self, parent: Any):
        self._parent = parent
        self._label = "Label"
        self._tooltip = None
        self._dest = None
        self._itype = InputType.TEXT
        self._access_type = AccessType.READ_WRITE
        self._min_max_length = 5, 30
        self._value = ""
        self._validator = InputValidator.anything(), self._validate_field

    def label(self, label: str) -> "FieldBuilder":
        self._label = label
        return self

    def tooltip(self, tooltip: str) -> "FieldBuilder":
        self._tooltip = tooltip
        return self

    def dest(self, dest: str) -> "FieldBuilder":
        self._dest = dest
        return self

    def itype(self, itype: str) -> "FieldBuilder":
        self._itype = InputType.of_value(itype)
        return self

    def min_max_length(self, min_length: int, max_length: int) -> "FieldBuilder":
        check_argument(max_length >= min_length, "Invalid field length: ({}-{})", min_length, max_length)
        check_argument(max_length > 0 and min_length >= 0, "Invalid field length: ({}-{})", min_length, max_length)
        self._min_max_length = min_length, max_length
        return self

    def access_type(self, access_type: str) -> "FieldBuilder":
        self._access_type = AccessType.of_value(access_type)
        return self

    def value(self, value: Any | None) -> "FieldBuilder":
        self._value = value
        return self

    def validator(
        self, input_validator: InputValidator = None, field_validator: FieldValidator_Fn = None
    ) -> "FieldBuilder":
        self._validator = input_validator, field_validator or self._validate_field
        return self

    def build(self) -> Any:
        if self._itype == InputType.CHECKBOX:
            self._value = to_bool(str(self._value))
        elif self._itype == InputType.SELECT:
            parts = re.split(VALUE_SEPARATORS, re.sub("[<>]", "", str(self._value or "")))
            self._min_max_length = len(min(parts, key=len)), len(max(parts, key=len))
        elif self._itype == InputType.MASKED:
            _, mask = unpack_masked(str(self._value))
            min_max = reduce(add, list(map(mask.count, MASK_SYMBOLS)))
            self._min_max_length = min_max, min_max
        self._dest = self._dest or snakecase(self._label)
        self._parent.fields.append(
            FormField(
                self._label,
                self._dest,
                self._itype,
                self._min_max_length[0],
                self._min_max_length[1],
                self._access_type,
                self._value,
                self._validator[0],
                self._validator[1],
                self._tooltip
            )
        )

        return self._parent
