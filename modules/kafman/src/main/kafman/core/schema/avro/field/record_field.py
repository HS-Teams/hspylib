#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Kafman
@package: kafman.core.schema.avro.field
   @file: record_field.py
@created: Wed, 1 Jun 2022
 @author: "<B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: "https://github.com/yorevs/hspylib")
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from avro.schema import Field
from kafman.core.schema.avro.avro_type import AvroType
from kafman.core.schema.schema_field import SchemaField
from kafman.core.schema.widget_utils import MISSING
from typing import Any, Tuple


class RecordField(SchemaField):
    def __init__(
        self,
        name: str,
        doc: str,
        fields: Tuple[Field, ...],
        required: bool = True,
        default: Any = MISSING,
        *,
        nullable: bool = False,
        record_name: str = "",
    ):
        super().__init__(
            name, doc, AvroType.RECORD, default, required=required, nullable=nullable
        )
        self.fields = fields
        self.record_name = record_name
