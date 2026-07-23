#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Kafman
@package: kafman.core.schema.json.property
   @file: json_type.py
@created: Wed, 8 Jun 2022
 @author: "<B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: "https://github.com/yorevs/hspylib")
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from hspylib.core.enums.enumeration import Enumeration
from typing import Any


class JsonType(Enumeration):
    """TODO"""

    # fmt: off
    NULL            = 'null'
    STRING          = 'string'   # string|bytes|enum|fixed
    NUMBER          = 'number'   # float|double
    INTEGER         = 'integer'  # int|long
    OBJECT          = 'object'   # record|map
    ARRAY           = 'array'    # array
    BOOLEAN         = 'boolean'  # bool
    ENUM            = 'enum'     # array or string enumeration
    UNION           = 'union'    # anyOf/oneOf or multiple JSON types
    # fmt: on

    def empty_value(self) -> Any:
        """TODO"""

        values: dict[str, Any] = {
            "null": None,
            "boolean": False,
            "integer": 0,
            "number": 0.0,
            "object": {},
            "array": [],
        }
        return values.get(self.value, "")

    def is_primitive(self) -> bool:
        return self.value not in ["object", "array", "union"]

    def is_object(self):
        """TODO"""
        return self.value == "object"
