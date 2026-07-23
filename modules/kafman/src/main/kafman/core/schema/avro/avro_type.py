#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Kafman
@package: kafman.core.schema.avro
   @file: avro_type.py
@created: Fri, 01 Apr 2022
 @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: https://github.com/yorevs/hspylib
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from avro.schema import Schema
from hspylib.core.enums.enumeration import Enumeration
from typing import Any


class AvroType(Enumeration):
    """TODO"""

    # fmt: off
    NULL            = 'null'        # No value
    BOOLEAN         = 'boolean'     # A binary value
    INT             = 'int'         # 32-bit signed integer
    LONG            = 'long'        # 64-bit signed integer
    FLOAT           = 'float'       # Single precision (32-bit) IEEE 754 floating-point number
    DOUBLE          = 'double'      # Double precision (64-bit) IEEE 754 floating-point number
    BYTES           = 'bytes'       # Sequence of 8-bit unsigned bytes
    STRING          = 'string'      # Unicode character sequence
    RECORD          = 'record'      # Records use the type name "record"
    ENUM            = 'enum'        # Enums use the type name "enum"
    ARRAY           = 'array'       # Arrays use the type name "array"
    MAP             = 'map'         # Maps use the type name "map"
    UNION           = 'union'       # Unions, as mentioned above, are represented using JSON arrays
    FIXED           = 'fixed'       # Fixed uses the type name "fixed"
    # fmt: on

    @classmethod
    def of_type(cls, r_type: Schema) -> "AvroType":
        """TODO"""
        return cls.of_value(r_type.type)

    def empty_value(self) -> Any:
        """TODO"""

        values: dict[str, Any] = {
            "null": None,
            "boolean": False,
            "int": 0,
            "long": 0,
            "float": 0.0,
            "double": 0.0,
            "bytes": b"",
            "array": [],
            "map": {},
            "record": {},
        }
        return values.get(self.value, "")

    def is_primitive(self):
        return self.value not in ["record", "enum", "array", "map", "union", "fixed"]

    def is_union(self):
        return self.value == "union"

    def is_record(self):
        return self.value == "record"
