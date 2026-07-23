#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Create typed form fields from Apache Avro schema nodes."""

from __future__ import annotations

from abc import ABC
from typing import Any, Iterable, List

from avro.schema import (
    ArraySchema,
    EnumSchema,
    Field,
    FixedSchema,
    MapSchema,
    PrimitiveSchema,
    RecordSchema,
    Schema,
    UnionSchema,
)
from hspylib.core.exception.exceptions import InvalidStateError
from kafman.core.schema.avro.avro_type import AvroType
from kafman.core.schema.avro.field.array_field import ArrayField
from kafman.core.schema.avro.field.enum_field import EnumField
from kafman.core.schema.avro.field.fixed_field import FixedField
from kafman.core.schema.avro.field.map_field import MapField
from kafman.core.schema.avro.field.primitive_field import PrimitiveField
from kafman.core.schema.avro.field.record_field import RecordField
from kafman.core.schema.avro.field.union_field import UnionField
from kafman.core.schema.schema_field import SchemaField
from kafman.core.schema.widget_utils import MISSING


class FieldFactory(ABC):
    @classmethod
    def create_field(cls, field: Field) -> SchemaField:
        name = field.name
        doc = field.doc or f"The {name} field"
        default = field.default if field.has_default else MISSING
        required = not field.has_default
        return cls._create_for_schema(name, doc, field.type, default, required)

    @classmethod
    def create_schema_field(
        cls,
        name: str,
        doc: str,
        schema: Schema,
        default: Any = MISSING,
        required: bool = True,
    ) -> SchemaField:
        """Create a field for a top-level or otherwise anonymous schema node."""
        return cls._create_for_schema(name, doc, schema, default, required)

    @classmethod
    def _create_for_schema(
        cls,
        name: str,
        doc: str,
        schema: Schema,
        default: Any,
        required: bool,
        *,
        nullable: bool = False,
    ) -> SchemaField:
        if isinstance(schema, UnionSchema):
            branches = list(schema.schemas)
            non_null = [
                branch for branch in branches if getattr(branch, "type", None) != "null"
            ]
            is_nullable = len(non_null) != len(branches)
            if len(non_null) == 1:
                return cls._create_for_schema(
                    name, doc, non_null[0], default, required, nullable=is_nullable
                )
            if not non_null:
                return PrimitiveField(
                    name, doc, AvroType.NULL, default, required, nullable=True
                )
            return UnionField(
                name, doc, branches, default, required, nullable=is_nullable
            )

        avro_type = AvroType.of_type(schema)
        if isinstance(schema, PrimitiveSchema):
            constraints = {
                key: value
                for key, value in getattr(schema, "props", {}).items()
                if key not in {"type", "logicalType"}
            }
            logical_type = getattr(schema, "logical_type", None)
            if logical_type:
                constraints["logicalType"] = logical_type
            return PrimitiveField(
                name,
                doc,
                avro_type,
                default,
                required,
                nullable=nullable,
                constraints=constraints,
            )
        if isinstance(schema, EnumSchema):
            return EnumField(
                name, doc, list(schema.symbols), default, required, nullable=nullable
            )
        if isinstance(schema, ArraySchema):
            return ArrayField(
                name, doc, schema.items, default, required, nullable=nullable
            )
        if isinstance(schema, MapSchema):
            return MapField(
                name, doc, schema.values, default, required, nullable=nullable
            )
        if isinstance(schema, RecordSchema):
            return RecordField(
                name,
                doc,
                tuple(schema.fields),
                required,
                default,
                nullable=nullable,
                record_name=schema.fullname,
            )
        if isinstance(schema, FixedSchema):
            return FixedField(
                name, doc, schema.size, default, required, nullable=nullable
            )
        raise InvalidStateError(f"Invalid Avro field type: {schema}")

    @classmethod
    def create_schema_fields(cls, fields: Iterable[Field]) -> List[SchemaField]:
        return [cls.create_field(field) for field in fields]

    @staticmethod
    def is_required(field: Field) -> bool:
        return not field.has_default
