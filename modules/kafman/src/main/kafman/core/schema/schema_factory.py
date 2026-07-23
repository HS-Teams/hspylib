#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Kafman
@package: kafman.core.schema
   @file: schema_factory.py
@created: Thu, 5 Aug 2021
 @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: https://github.com/yorevs/hspylib
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from abc import ABC
from hspylib.core.exception.exceptions import InvalidStateError
from kafman.core.schema.avro.avro_schema import AvroSchema
from kafman.core.schema.json.json_schema import JsonSchema
from kafman.core.schema.kafka_schema import KafkaSchema
from typing import Tuple, Type

import os


class SchemaFactory(ABC):
    """Factory method to create Avro schemas"""

    _schemas_types: Tuple[Type[AvroSchema], Type[JsonSchema]] = (AvroSchema, JsonSchema)

    @classmethod
    def create_schema(cls, filepath: str, registry_url: str) -> KafkaSchema:
        """Create a schema based on the provided file extension"""
        _, f_ext = os.path.splitext(filepath)
        schema_cls = next(
            (schema for schema in cls._schemas_types if schema.supports(f_ext)), None
        )
        if schema_cls is None:
            raise InvalidStateError(
                f'No schema implementation supports extension "{f_ext}"'
            )

        return schema_cls(filepath, registry_url)
