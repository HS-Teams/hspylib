#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Kafman
@package: kafman.core.schema
   @file: json_schema.py
@created: Sun, 18 Jul 2021
 @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: https://github.com/yorevs/hspylib
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from confluent_kafka.serialization import (
    SerializationContext,
    StringDeserializer,
    StringSerializer,
)
from hspylib.core.enums.charset import Charset
from hspylib.core.namespace import Namespace
from hqt.promotions.hstacked_widget import HStackedWidget
from kafman.core.schema.kafka_schema import KafkaSchema
from kafman.core.schema.schema_field import SchemaField
from kafman.core.schema.schema_type import SchemaType
from kafman.views.promotions.form_pane import FormPane
from typing import List, Optional


class PlainSchema(KafkaSchema):
    """String schema serializer/deserializer"""

    def to_dict(self, obj: str, ctx: SerializationContext) -> dict:
        return {}

    def from_dict(self, obj: dict, ctx: SerializationContext) -> str:
        return str(Namespace("PlainSchemaObject"))

    def __init__(self, charset: Charset = Charset.UTF_8):
        super().__init__(SchemaType.PLAIN, charset=charset)

    def __str__(self):
        return f"[{self._schema_type}] type=plaintext"

    def _parse(self) -> None:
        pass

    def create_schema_form_widget(
        self,
        form_stack: HStackedWidget,
        parent_pane: Optional[FormPane] = None,
        form_name: Optional[str] = None,
        fields: Optional[List[SchemaField]] = None,
    ) -> int:
        """Plain text messages do not require a generated form."""
        return 0

    def settings(self) -> dict:
        return {
            "key.serializer": StringSerializer(str(self._charset)),
            "value.serializer": StringSerializer(str(self._charset)),
            "key.deserializer": StringDeserializer(str(self._charset)),
            "value.deserializer": StringDeserializer(str(self._charset)),
        }
