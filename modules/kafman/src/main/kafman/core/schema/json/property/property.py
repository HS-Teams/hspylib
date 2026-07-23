#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Intermediate JSON Schema property representation."""

from __future__ import annotations

from typing import Any, Optional

from kafman.core.schema.json.json_type import JsonType
from kafman.core.schema.widget_utils import MISSING


class Property:
    def __init__(
        self,
        name: str,
        title: str,
        description: str,
        s_type: JsonType,
        default: Any = MISSING,
        required: bool = True,
        *,
        nullable: bool = False,
        schema: Optional[dict[str, Any]] = None,
    ):
        self.name = name
        self.title = title
        self.description = description
        self.type = s_type
        self.default = default
        self.required = required
        self.nullable = nullable
        self.schema = schema or {}
        self.all_properties: tuple["Property", ...] = ()
        self.items: dict[str, Any] = {}
        self.enum: list[Any] = list(self.schema.get("enum", []))

    def set_items(self, items: dict[str, Any]) -> None:
        self.items = items
