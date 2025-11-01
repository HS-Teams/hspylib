#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
   @project: HsPyLib
   @package: hspylib.core.tools
      @file: json_path.py
   @created: Tue, 4 May 2021
    @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
      @site: https://github.com/yorevs/hspylib
   @license: MIT - Please refer to <https://opensource.org/licenses/MIT>

   Copyright·(c)·2024,·HSPyLib
"""

from pyparsing import unicode
from typing import Any, TypeAlias, Union

import re

JsonElement: TypeAlias = Union[list, dict, unicode]


class JsonPath:
    """Navigate and"""

    RE_JSON_NAME = "[a-zA-Z0-9_\\- ]"
    RE_JSON_ARRAY_INDEX = "[0-9]{1,}"

    def __init__(
        self, separator: str = ".", json_name_re: str = RE_JSON_NAME, json_array_index_re: str = RE_JSON_ARRAY_INDEX
    ):
        """Construction"""

        self.separator = separator
        self.jsonNameRe = json_name_re
        self.jsonArrayIndexRe = json_array_index_re
        self.pat_elem = None
        self.pat_sel_elem_val = None
        self.pat_sub_expr = None
        self.pat_sub_expr_val = None

    def _find_next_element(
        self, root_element: JsonElement, match_name: str, match_value: Any = None, fetch_parent: bool = False
    ) -> JsonElement:
        """Find the next element in the list matching the specified value."""

        selected_element = root_element
        if isinstance(selected_element, list):
            for nextInList in root_element:
                if isinstance(nextInList, dict):
                    selected_element = nextInList.get(match_name)
                    if selected_element and (match_value is None or (match_value and selected_element == match_value)):
                        # To return the parent element instead of the leaf
                        if fetch_parent:
                            selected_element = nextInList
                        break
                    selected_element = None
                elif isinstance(nextInList, unicode):
                    selected_element = root_element
                elif isinstance(nextInList, list):
                    selected_element = self._find_next_element(nextInList, match_name, match_value)
        elif isinstance(selected_element, dict):
            el = selected_element.get(match_name)
            if el and (match_value is None or (match_value and el == match_value)):
                # To return the parent element instead of the leaf
                if not fetch_parent:
                    selected_element = el
            else:
                selected_element = None
        else:
            selected_element = None

        return selected_element

    def _find_in_sub_expr(
        self, sub_expr: JsonElement, sub_sel_el: JsonElement, pat_subst_expr_val: Any, fetch_parent: bool = False
    ) -> JsonElement:
        """Find the element in the sub-expressions."""

        for nextSubExpr in sub_expr:
            if nextSubExpr:
                sub_parts = re.search(pat_subst_expr_val, nextSubExpr)
                sub_elem_id = sub_parts.group(1)
                sub_elem_val = sub_parts.group(3)
                sub_sel_el = self._find_next_element(sub_sel_el, sub_elem_id, sub_elem_val, fetch_parent)

        return sub_sel_el

    # pylint: disable=too-many-branches,consider-using-f-string
    def select(self, root_element: JsonElement, search_path: str, fetch_parent: bool = False) -> JsonElement:
        """
        Get the json element through its path. Returned object is either [dict, list or unicode].

        Search patterns:
          1. elem1.elem2
          2. elem1.elem2[index]
          3. elem1.elem2{property}
          4. elem1.elem2{property}[index]
          5. elem1.elem2{property<value>}
          6. elem1.elem2[index].elem3
          7. elem1.elem2{property}.elem3
          8. elem1.elem2{property<value>}.elem3
          9. elem1.elem2{property<value>}[index].elem3
         10. elem1.elem2{property<value>}.{property2<value2>}.elem3
        """

        self.pat_elem = f"{self.jsonNameRe}+"
        self.pat_sel_elem_val = "(%s)?((\\{(%s)(<(%s)>)?\\})+)(\\[(%s)\\])?" % (
            self.pat_elem,
            self.pat_elem,
            self.pat_elem,
            self.jsonArrayIndexRe,
        )
        self.pat_sub_expr = "(\\{%s\\})" % self.pat_elem
        self.pat_sub_expr_val = "\\{(%s)(<(%s)>)?\\}" % (self.pat_elem, self.pat_elem)
        selected_element = root_element

        # pylint: disable=too-many-nested-blocks
        try:
            search_tokens = search_path.split(self.separator)
            for nextElement in search_tokens:
                if nextElement.find("{") >= 0:  # Next element has nested elements
                    parts = re.search(self.pat_sel_elem_val, nextElement)
                    sel_elem_id = parts.group(1)
                    sub_parts = parts.group(2)
                    elem_array_group = parts.group(7)
                    elem_array_index = parts.group(8)
                    sub_expressions = re.compile(self.pat_sub_expr).split(sub_parts)
                    if sel_elem_id and isinstance(selected_element, dict):
                        selected_element = selected_element.get(sel_elem_id)
                    if selected_element:
                        # Our first element is a list, so we will have to loop and find all the elements
                        # and sub expressions in it.
                        if isinstance(selected_element, list):
                            for nextInList in selected_element:
                                sub_selected_element = self._find_in_sub_expr(
                                    sub_expressions, nextInList, self.pat_sub_expr_val, fetch_parent
                                )
                                # It sub_selected_element is not null then we have found what we wanted.
                                if sub_selected_element:
                                    selected_element = sub_selected_element
                                    break
                        # Check if there are indexed elements.
                        if elem_array_group and elem_array_index and isinstance(selected_element, list):
                            selected_element = selected_element[int(elem_array_index)]

                elif nextElement.find("[") >= 0:  # Next element is indexed
                    pat_sel_elem_idx = f"({self.pat_elem})\\[({self.jsonArrayIndexRe})\\]"
                    parts = re.search(pat_sel_elem_idx, nextElement)
                    sub_elem_id = parts.group(1)
                    elem_array_index = parts.group(2)
                    # TODO Implement subarray like elem[0][1][2]
                    if sub_elem_id is not None and elem_array_index is not None:
                        el = selected_element.get(sub_elem_id)
                        if isinstance(el, list):
                            selected_element = el[int(elem_array_index)]
                else:  # Next element is simple
                    selected_element = selected_element.get(nextElement)
        except (AttributeError, IndexError):
            selected_element = None

        return selected_element
