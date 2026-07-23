#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Avro union field represented by a JSON value editor."""

from typing import Any, Iterable

from kafman.core.schema.avro.avro_type import AvroType
from kafman.core.schema.schema_field import SchemaField
from kafman.core.schema.widget_utils import MISSING


class UnionField(SchemaField):
    def __init__(
        self,
        name: str,
        doc: str,
        branches: Iterable[Any],
        default: Any = MISSING,
        required: bool = True,
        *,
        nullable: bool = False,
    ):
        super().__init__(name, doc, AvroType.UNION, default, required, nullable=nullable)
        self.branches = tuple(branches)
