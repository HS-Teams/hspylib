#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Kafman
@package: kafman.core.schema.avro.field
   @file: array_field.py
@created: Wed, 1 Jun 2022
 @author: "<B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: "https://github.com/yorevs/hspylib")
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from kafman.core.schema.avro.avro_type import AvroType
from kafman.core.schema.schema_field import SchemaField
from kafman.core.schema.widget_utils import MISSING
from typing import Any


class ArrayField(SchemaField):
    def __init__(
        self,
        name: str,
        doc: str,
        items: Any,
        default: Any = MISSING,
        required: bool = True,
        *,
        nullable: bool = False,
    ):
        super().__init__(
            name,
            doc,
            AvroType.ARRAY,
            default,
            required=required,
            nullable=nullable,
            item_type=items,
        )
        self.items = items
