#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Kafman
@package: kafman.core.schema.json.property
   @file: enum_property.py
@created: Fri, 1 Jul 2022
 @author: "<B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: "https://github.com/yorevs/hspylib")
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from kafman.core.schema.json.json_type import JsonType
from kafman.core.schema.schema_field import SchemaField
from kafman.core.schema.widget_utils import MISSING
from typing import Any, List, Optional


class EnumProperty(SchemaField):
    def __init__(
        self,
        name: str,
        description: str,
        symbols: List[Any],
        default: Any = MISSING,
        required: bool = True,
        *,
        nullable: bool = False,
        constraints: Optional[dict] = None,
    ):
        super().__init__(
            name,
            description,
            JsonType.ENUM,
            default,
            required,
            nullable=nullable,
            constraints=constraints,
        )
        self.symbols = symbols
