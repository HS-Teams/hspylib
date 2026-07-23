#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Kafman
@package: kafman.core.schema.avro
   @file: avro_schema.py
@created: Sat, 17 Jul 2021
 @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: https://github.com/yorevs/hspylib
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from confluent_kafka.schema_registry.avro import AvroDeserializer, AvroSerializer
from confluent_kafka.serialization import StringDeserializer, StringSerializer
from avro.io import validate as validate_avro
from fastavro.validation import validate as validate_schema
from hqt.promotions.hstacked_widget import HStackedWidget
from hspylib.core.enums.charset import Charset
from hspylib.core.preconditions import check_not_none
from kafman.core.consumer.consumer_config import ConsumerConfig
from kafman.core.producer.producer_config import ProducerConfig
from kafman.core.schema.avro.field.field_factory import FieldFactory
from kafman.core.schema.avro.field.record_field import RecordField
from kafman.core.schema.kafka_schema import KafkaSchema
from kafman.core.schema.schema_field import SchemaField
from kafman.core.schema.schema_type import SchemaType
from kafman.views.promotions.form_pane import FormPane
from typing import Any, List, Optional

import avro.schema as schema_parser
import base64
import json
from decimal import Decimal
from pathlib import Path


class AvroSchema(KafkaSchema):
    """Apache AVRO schema serializer/deserializer
    Documentation:
     - https://avro.apache.org/docs/current/spec.html
     - https://avro.apache.org/docs/current/gettingstartedpython.html
    Additional Ref: https://docs.confluent.io/5.3.0/schema-registry/serializer-formatter.html

     E.g:.
     {
       "type": "record",
       "name": "myRecord",
       "fields": [
           {"name": "name",  "type": "string" }
         , {"name": "calories", "type": "float" }
         , {"name": "colour", "type": "string" }
       ]
     }
    """

    @classmethod
    def extensions(cls) -> List[str]:
        return ["*.avsc"]

    def __init__(
        self, filepath: str, registry_url: str, charset: Charset = Charset.UTF_8
    ):
        super().__init__(SchemaType.AVRO, filepath, registry_url, charset)

    def settings(self) -> dict:
        """TODO"""
        return {
            ProducerConfig.KEY_SERIALIZER: StringSerializer(self._charset.value),
            ProducerConfig.VALUE_SERIALIZER: AvroSerializer(
                self._schema_client, self._content_text, self.to_dict
            ),
            ConsumerConfig.KEY_DESERIALIZER: StringDeserializer(self._charset.value),
            ConsumerConfig.VALUE_DESERIALIZER: AvroDeserializer(
                self._schema_client, self._content_text, self.from_dict
            ),
        }

    def to_dict(self, obj: str, ctx) -> Any:  # pylint: disable=unused-argument
        """Convert form JSON into values accepted by the Avro writer."""
        value = json.loads(obj)
        if (
            self._parsed.type != "record"
            and isinstance(value, dict)
            and "value" in value
        ):
            value = value["value"]
        return self._coerce_value(value, self._parsed)

    def from_dict(self, obj: dict, ctx) -> str:  # pylint: disable=unused-argument
        return json.dumps(
            obj,
            default=lambda value: (
                f"base64:{base64.b64encode(value).decode('ascii')}"
                if isinstance(value, bytes)
                else str(value)
            ),
        )

    def validate(self, json_form: Any) -> None:
        value = json_form
        if (
            self._parsed.type != "record"
            and isinstance(value, dict)
            and "value" in value
        ):
            value = value["value"]
        validate_schema(value, self.get_content_dict())

    def create_schema_form_widget(
        self,
        form_stack: HStackedWidget,
        parent_pane: Optional[FormPane] = None,
        form_name: Optional[str] = None,
        fields: Optional[List[SchemaField]] = None,
        _visited: frozenset[str] = frozenset(),
    ) -> int:
        """Create the stacked frame with the form widget"""

        form_fields = fields if fields is not None else self._attributes.fields
        parsed_fullname = getattr(self._parsed, "fullname", None)
        if not _visited and parsed_fullname:
            _visited = frozenset({parsed_fullname})

        if not form_fields or len(form_fields) <= 0:
            return 0

        form_name = form_name if form_name is not None else self._schema_name
        form_pane = FormPane(form_stack, parent_pane, form_name)
        index = form_stack.addWidget(form_pane)

        for row, field in enumerate(form_fields):
            check_not_none(field)
            req_label, label, widget = KafkaSchema.create_schema_form_row_widget(field)
            if isinstance(field, RecordField) and field.record_name not in _visited:
                record_fields = FieldFactory.create_schema_fields(field.fields)
                if isinstance(field.default, dict):
                    for child_field in record_fields:
                        if child_field.name in field.default:
                            child_field.apply_default(field.default[child_field.name])
                child_index = self.create_schema_form_widget(
                    form_stack,
                    form_pane,
                    field.name,
                    record_fields,
                    _visited | {field.record_name},
                )
                form_pane.add_form_button(
                    field.name, label, req_label, row, child_index, form_stack, field
                )
            else:
                form_pane.add_field(field.name, label, req_label, widget, row, field)

        if index > 0:
            parent_index = form_stack.indexOf(parent_pane)
            form_pane.add_back_button(parent_index, form_stack)

        return index

    def _parse(self) -> None:
        self._parsed = schema_parser.parse(self._content_text)

        assert self._filepath is not None
        self._schema_name = (
            getattr(self._parsed, "name", None) or Path(self._filepath).stem
        )
        self._attributes.name = getattr(self._parsed, "fullname", self._schema_name)
        self._attributes.namespace = getattr(self._parsed, "namespace", None)
        self._attributes.doc = getattr(self._parsed, "doc", None)

        field_type = self._parsed.type

        if "record" == field_type:
            self._attributes.fields = FieldFactory.create_schema_fields(
                getattr(self._parsed, "fields", ())
            )
        else:
            self._attributes.fields = [
                FieldFactory.create_schema_field(
                    "value", self._attributes.doc or "Schema value", self._parsed
                )
            ]

    @classmethod
    def _coerce_value(cls, value, schema):
        """Recursively coerce JSON-compatible form values to Avro-native values."""
        if value is None:
            return None
        schema_type = getattr(schema, "type", schema)
        logical_type = getattr(schema, "props", {}).get("logicalType")
        if logical_type == "decimal":
            return value if isinstance(value, Decimal) else Decimal(str(value))
        if schema_type in {"bytes", "fixed"}:
            if isinstance(value, bytes):
                return value
            text = str(value)
            return (
                base64.b64decode(text.removeprefix("base64:"), validate=True)
                if text.startswith("base64:")
                else text.encode("utf-8")
            )
        if schema_type in {"int", "long"}:
            return int(value)
        if schema_type in {"float", "double"}:
            return float(value)
        if schema_type == "boolean":
            return (
                value
                if isinstance(value, bool)
                else str(value).lower() in {"true", "1", "yes"}
            )
        if schema_type == "array":
            return [cls._coerce_value(item, schema.items) for item in value]
        if schema_type == "map":
            return {
                key: cls._coerce_value(item, schema.values)
                for key, item in value.items()
            }
        if schema_type == "record":
            fields = {field.name: field for field in schema.fields}
            return {
                key: (
                    cls._coerce_value(item, fields[key].type) if key in fields else item
                )
                for key, item in value.items()
            }
        if schema_type == "union":
            for branch in schema.schemas:
                if getattr(branch, "type", None) == "null":
                    continue
                try:
                    candidate = cls._coerce_value(value, branch)
                    if validate_avro(branch, candidate):
                        return candidate
                except (TypeError, ValueError, AttributeError):
                    continue
            raise ValueError(f"Value {value!r} does not match any Avro union branch")
        return value
