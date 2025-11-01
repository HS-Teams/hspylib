#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
   @project: HsPyLib
   @package: hspylib.core.tools
      @file: object_mapper.py
   @created: Fri, 28 Feb 2024
    @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior"
      @site: https://github.com/yorevs/hspylib
   @license: MIT - Please refer to <https://opensource.org/licenses/MIT>

   Copyright (c) 2024, HomeSetup
"""

from hspylib.core.exception.exceptions import InvalidJsonMapping, InvalidMapping
from hspylib.core.enums.enumeration import Enumeration
from hspylib.core.metaclass.singleton import Singleton
from inspect import isclass
from json import JSONDecodeError
from types import SimpleNamespace
from typing import Any, Callable, Dict, Optional, Set, Type, TypeAlias

import inspect
import json

FnConverter: TypeAlias = Callable[[Any, Type], Any]


class ObjectMapper(metaclass=Singleton):
    """Provide a utility class to convert one object into the other, and vice-versa."""

    INSTANCE: "ObjectMapper"

    class ConversionMode(Enumeration):
        """TODO"""

        # fmt: off
        STANDARD    = '_standard_converter'
        STRICT      = '_strict_converter'
        # fmt: on

    @staticmethod
    def _hash(type_from: Any, type_to: Type) -> str:
        """Create a hash value for both classes in a way that"""
        return (
            str(hash(type_from.__name__) + hash(type_to.__name__))
            if isclass(type_from)
            else str(hash(type_from.__class__.__name__) + hash(type_to.__name__))
        )

    @classmethod
    def _strict_converter(cls, type1: Any, type2: Type) -> Any:
        """Default conversion function using the object variables. Attribute names must be equal in both classes."""
        return type2(**vars(type1))

    @classmethod
    def _standard_converter(cls, type1: Any, type2: Type) -> Any:
        """Default conversion function using the object variables. Attribute names must be equal in both classes."""
        source_attrs = vars(type1)
        target_fields = cls._collect_supported_fields(type2)
        attrs = {field: source_attrs[field] for field in target_fields if field in source_attrs}
        return type2(**attrs)

    @classmethod
    def _collect_supported_fields(cls, type2: Type) -> Set[str]:
        """Collect all supported fields for the target type based on annotations and the constructor signature."""
        target_fields: Set[str] = set()
        try:
            signature = inspect.signature(type2)
        except (TypeError, ValueError):
            signature = None

        if signature:
            for name, param in signature.parameters.items():
                if name == "self":
                    continue
                if param.kind in (
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    inspect.Parameter.KEYWORD_ONLY,
                ):
                    target_fields.add(name)

        annotations = getattr(type2, "__annotations__", {})
        target_fields.update(annotations.keys())

        return target_fields

    @classmethod
    def get_class_attributes(cls, clazz: Type):
        return [
            item[0]
            for item in inspect.getmembers(clazz)
            if not callable(getattr(clazz, item[0])) and not item[0].startswith("__")
        ]

    def __init__(self):
        self._converters: Dict[str, FnConverter] = {}

    @property
    def strict(self) -> ConversionMode:
        return self.ConversionMode.STRICT

    @property
    def standard(self) -> ConversionMode:
        return self.ConversionMode.STANDARD

    def of_json(self, json_string: str, to_class: Type, mode: ConversionMode = ConversionMode.STANDARD) -> Any:
        """ "Convert a JSON string to an object on the provided type."""
        if not json_string:
            return ""
        try:
            json_obj = json.loads(json_string, object_hook=lambda d: SimpleNamespace(**d))
            ret_val = self.convert(json_obj, to_class, mode)
        except (TypeError, InvalidMapping, JSONDecodeError) as err:
            if mode == self.ConversionMode.STRICT:
                raise InvalidJsonMapping(f"Could not decode JSON string '{json_string}' => {str(err)}") from err
            ret_val = json_string
        return ret_val

    def convert(self, from_obj: Any, to_class: Type, mode: ConversionMode = ConversionMode.STANDARD) -> Any:
        """Convert one object into another of the provided class type."""
        mapping_hash = self._hash(from_obj, to_class)
        try:
            fn_converter = self._get_converter(mapping_hash, mode)
            obj = fn_converter(from_obj, to_class)
        except Exception as err:
            raise InvalidMapping(f"Can't convert {type(from_obj)} into {to_class}") from err
        return obj

    def register(self, type1: Any, type2: Any, fn_converter: FnConverter) -> None:
        """Register a new converter for the given types."""
        self._converters[self._hash(type1, type2)] = fn_converter

    def _get_converter(self, mapping_hash: str, mode: ConversionMode) -> Optional[FnConverter]:
        """Retrieve the converter for the provided the mapping hash."""
        default_fb = getattr(self, mode.value)
        return next((c for h, c in self._converters.items() if h == mapping_hash), default_fb)


assert (object_mapper := ObjectMapper().INSTANCE) is not None
