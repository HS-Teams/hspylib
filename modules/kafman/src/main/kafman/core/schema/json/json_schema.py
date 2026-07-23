#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Kafman
@package: kafman.core.schema.json
   @file: json_schema.py
@created: Sun, 18 Jul 2021
 @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: https://github.com/yorevs/hspylib
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from confluent_kafka.schema_registry.json_schema import JSONDeserializer, JSONSerializer
from confluent_kafka.serialization import StringDeserializer, StringSerializer
from hqt.promotions.hstacked_widget import HStackedWidget
from hspylib.core.enums.charset import Charset
from hspylib.core.preconditions import check_not_none
from jsonschema import validate as validate_schema
from kafman.core.consumer.consumer_config import ConsumerConfig
from kafman.core.producer.producer_config import ProducerConfig
from kafman.core.schema.json.json_parser import JsonParser
from kafman.core.schema.json.property.object_property import ObjectProperty
from kafman.core.schema.json.property.property_factory import PropertyFactory
from kafman.core.schema.kafka_schema import KafkaSchema
from kafman.core.schema.schema_field import SchemaField
from kafman.core.schema.schema_type import SchemaType
from kafman.views.promotions.form_pane import FormPane
from typing import Any, List, Optional

import json


class JsonSchema(KafkaSchema):
    """Json schema serializer/deserializer
    Documentation: https://json-schema.org/
    Additional Ref: https://docs.confluent.io/5.3.0/schema-registry/serializer-formatter.html

    E.g:.
    {
       "definitions" : {
         "record:myRecord" : {
           "type" : "object",
           "required" : [ "name", "calories" ],
           "additionalProperties" : false,
           "properties" : {
             "name" : {"type" : "string"},
             "calories" : {"type" : "number"},
             "colour" : {"type" : "string"}
           }
         }
       },
       "$ref" : "#/definitions/record:myRecord"
     }
    """

    @classmethod
    def extensions(cls) -> List[str]:
        return ["*.json"]

    def __init__(
        self, filepath: str, registry_url: str, charset: Charset = Charset.UTF_8
    ):
        super().__init__(SchemaType.JSON, filepath, registry_url, charset)

    def settings(self) -> dict:
        return {
            ProducerConfig.KEY_SERIALIZER: StringSerializer(self._charset.value),
            ProducerConfig.VALUE_SERIALIZER: JSONSerializer(
                self._content_text, self._schema_client, self.to_dict
            ),
            ConsumerConfig.KEY_DESERIALIZER: StringDeserializer(self._charset.value),
            ConsumerConfig.VALUE_DESERIALIZER: JSONDeserializer(
                self._content_text, self.from_dict
            ),
        }

    def to_dict(self, obj: str, ctx) -> Any:  # pylint: disable=unused-argument
        value = json.loads(obj)
        if (
            self._parsed.type != "object"
            and isinstance(value, dict)
            and "value" in value
        ):
            return value["value"]
        return value

    def from_dict(self, obj: Any, ctx) -> str:  # pylint: disable=unused-argument
        return json.dumps(obj)

    def validate(self, json_form: Any) -> None:
        value = json_form
        if (
            self._parsed.type != "object"
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
    ) -> int:
        """Create the stacked frame with the form widget"""

        form_fields = fields if fields is not None else self._attributes.fields

        if not form_fields or len(form_fields) <= 0:
            return 0

        form_name = form_name if form_name is not None else self._schema_name
        form_pane = FormPane(form_stack, parent_pane, form_name)
        index = form_stack.addWidget(form_pane)

        for row, field in enumerate(form_fields):
            check_not_none(field)
            req_label, label, widget = KafkaSchema.create_schema_form_row_widget(field)
            if isinstance(field, ObjectProperty):
                object_props = PropertyFactory.create_schema_fields(field.properties)
                if isinstance(field.default, dict):
                    for child_field in object_props:
                        if child_field.name in field.default:
                            child_field.apply_default(field.default[child_field.name])
                child_index = self.create_schema_form_widget(
                    form_stack, form_pane, field.name, object_props
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
        """TODO"""

        self._parsed = JsonParser.parse(self._content_dict, self._filepath)

        self._schema_name = self._parsed.title or "JSON Schema"
        self._attributes.name = self._schema_name
        self._attributes.namespace = self._parsed.schema
        self._attributes.doc = (
            self._parsed.description if self._parsed.description else "<no-description>"
        )

        field_type = self._parsed.type

        if "object" == field_type:
            self._attributes.fields = PropertyFactory.create_schema_fields(
                self._parsed.properties
            )
        else:
            root_property = JsonParser._parse_properties(
                {"value": self._parsed.raw},
                ["value"],
                self._parsed.raw,
                JsonParser._load_catalog(self._filepath),
            )
            self._attributes.fields = PropertyFactory.create_schema_fields(
                root_property
            )
