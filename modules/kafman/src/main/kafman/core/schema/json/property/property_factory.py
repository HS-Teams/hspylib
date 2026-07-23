#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Create typed form fields from parsed JSON Schema properties."""

from abc import ABC
from typing import Iterable, List

from hspylib.core.exception.exceptions import InvalidStateError
from kafman.core.schema.json.json_type import JsonType
from kafman.core.schema.json.property.array_property import ArrayProperty
from kafman.core.schema.json.property.enum_property import EnumProperty
from kafman.core.schema.json.property.object_property import ObjectProperty
from kafman.core.schema.json.property.primitive_property import PrimitiveProperty
from kafman.core.schema.json.property.property import Property
from kafman.core.schema.schema_field import SchemaField


class PropertyFactory(ABC):
    @staticmethod
    def create_field(prop: Property) -> SchemaField:
        name = prop.name
        doc = prop.description or prop.title or f"The {name} property"
        constraints = prop.schema
        if prop.enum and prop.type != JsonType.ARRAY:
            return EnumProperty(
                name,
                doc,
                [value for value in prop.enum if value is not None],
                prop.default,
                prop.required,
                nullable=prop.nullable,
                constraints=constraints,
            )
        if prop.type.is_primitive():
            return PrimitiveProperty(
                name,
                doc,
                prop.type,
                prop.default,
                prop.required,
                nullable=prop.nullable,
                constraints=constraints,
            )
        if prop.type == JsonType.ARRAY:
            return ArrayProperty(
                name,
                doc,
                prop.items,
                prop.default,
                prop.required,
                nullable=prop.nullable,
                constraints=constraints,
            )
        if prop.type == JsonType.OBJECT:
            return ObjectProperty(
                name,
                doc,
                prop.all_properties,
                prop.default,
                prop.required,
                nullable=prop.nullable,
                constraints=constraints,
            )
        if prop.type == JsonType.UNION:
            return PrimitiveProperty(
                name,
                doc,
                JsonType.UNION,
                prop.default,
                prop.required,
                nullable=prop.nullable,
                constraints=constraints,
            )
        raise InvalidStateError(f"Invalid JSON field type: {prop.type}")

    @staticmethod
    def create_schema_fields(fields: Iterable[Property]) -> List[SchemaField]:
        return [PropertyFactory.create_field(field) for field in fields]
