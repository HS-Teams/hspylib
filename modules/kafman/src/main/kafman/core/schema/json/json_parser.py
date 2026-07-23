#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""JSON Schema parser used to construct typed form fields."""

from __future__ import annotations

import json
from abc import ABC
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urldefrag

from hspylib.core.exception.exceptions import InvalidArgumentError
from jsonschema.validators import validator_for
from kafman.core.schema.json.json_type import JsonType
from kafman.core.schema.json.property.property import Property
from kafman.core.schema.widget_utils import MISSING


class JsonParser(ABC):
    class JsonSchemaData:
        def __init__(self):
            self.id: Optional[str] = None
            self.schema: Optional[str] = None
            self.title: Optional[str] = None
            self.description: Optional[str] = None
            self.properties: tuple[Property, ...] = ()
            self.required: list[str] = []
            self.type: Optional[str] = None
            self.raw: dict[str, Any] = {}

    @classmethod
    def parse(
        cls, schema_dict: dict[str, Any], filepath: Optional[str] = None
    ) -> "JsonSchemaData":
        validator = validator_for(schema_dict)
        validator.check_schema(schema_dict)
        catalog = cls._load_catalog(filepath)
        root = cls._resolve(schema_dict, schema_dict, catalog, set())

        schema = cls.JsonSchemaData()
        schema.raw = root
        schema.id = root.get("$id") or root.get("id")
        schema.schema = root.get("$schema")
        schema.title = root.get("title") or (
            Path(filepath).stem if filepath else "JSON Schema"
        )
        schema.description = root.get("description")
        schema.required = list(root.get("required", []))
        schema.type = cls._type_name(root)[0].value
        if schema.type == JsonType.OBJECT.value:
            schema.properties = cls._parse_properties(
                root.get("properties", {}), schema.required, root, catalog
            )
        return schema

    @classmethod
    def _parse_properties(
        cls,
        properties: dict[str, Any],
        required: list[str],
        root: dict[str, Any],
        catalog: dict[str, dict[str, Any]],
    ) -> tuple[Property, ...]:
        parsed: list[Property] = []
        for name, raw_schema in properties.items():
            prop_schema = cls._resolve(raw_schema, root, catalog, set())
            prop_type, nullable = cls._type_name(prop_schema)
            default = prop_schema["default"] if "default" in prop_schema else MISSING
            prop = Property(
                name,
                prop_schema.get("title", ""),
                prop_schema.get("description", ""),
                prop_type,
                default,
                name in required,
                nullable=nullable,
                schema=prop_schema,
            )
            if prop_type == JsonType.OBJECT:
                nested_required = list(prop_schema.get("required", []))
                prop.all_properties = cls._parse_properties(
                    prop_schema.get("properties", {}), nested_required, root, catalog
                )
            elif prop_type == JsonType.ARRAY:
                item_schema = prop_schema.get("items", {})
                if isinstance(item_schema, dict):
                    prop.set_items(cls._resolve(item_schema, root, catalog, set()))
            parsed.append(prop)
        return tuple(parsed)

    @staticmethod
    def _type_name(schema: dict[str, Any]) -> tuple[JsonType, bool]:
        raw_type = schema.get("type")
        nullable = False
        if isinstance(raw_type, list):
            nullable = "null" in raw_type
            candidates = [value for value in raw_type if value != "null"]
            if len(candidates) == 1:
                raw_type = candidates[0]
            else:
                return JsonType.UNION, nullable
        if raw_type is None:
            if any(key in schema for key in ("oneOf", "anyOf", "allOf")):
                return JsonType.UNION, nullable
            if "enum" in schema:
                values = [value for value in schema["enum"] if value is not None]
                nullable = len(values) != len(schema["enum"])
                if values:
                    first = values[0]
                    raw_type = (
                        "boolean"
                        if isinstance(first, bool)
                        else (
                            "integer"
                            if isinstance(first, int)
                            else "number" if isinstance(first, float) else "string"
                        )
                    )
            elif "properties" in schema or "additionalProperties" in schema:
                raw_type = "object"
        if raw_type is None:
            raise InvalidArgumentError(
                f"Unable to determine JSON type from schema: {schema}"
            )
        return JsonType.of_value(raw_type), nullable

    @staticmethod
    def _load_catalog(filepath: Optional[str]) -> dict[str, dict[str, Any]]:
        catalog: dict[str, dict[str, Any]] = {}
        if not filepath:
            return catalog
        for candidate in Path(filepath).parent.glob("*.json"):
            try:
                content = json.loads(candidate.read_text(encoding="utf-8"))
                catalog[str(candidate.resolve())] = content
                if identifier := content.get("$id") or content.get("id"):
                    catalog[identifier] = content
            except (OSError, json.JSONDecodeError):
                continue
        return catalog

    @classmethod
    def _resolve(
        cls,
        schema: dict[str, Any],
        root: dict[str, Any],
        catalog: dict[str, dict[str, Any]],
        seen: set[str],
    ) -> dict[str, Any]:
        if "$ref" not in schema:
            return schema
        reference = schema["$ref"]
        if reference in seen:
            return {
                "type": "object",
                "description": f"Recursive reference: {reference}",
            }
        seen = seen | {reference}
        document_ref, fragment = urldefrag(reference)
        document = root if not document_ref else catalog.get(document_ref)
        if document is None:
            raise InvalidArgumentError(
                f'Unable to resolve JSON Schema reference "{reference}"'
            )
        resolved: Any = document
        if fragment:
            for token in fragment.lstrip("/").split("/"):
                token = token.replace("~1", "/").replace("~0", "~")
                resolved = resolved[token]
        if not isinstance(resolved, dict):
            raise InvalidArgumentError(
                f'JSON Schema reference "{reference}" does not resolve to an object'
            )
        merged = dict(cls._resolve(resolved, document, catalog, seen))
        merged.update({key: value for key, value in schema.items() if key != "$ref"})
        return merged
