#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
   @project: HsPyLib
   @package: clitt.core.tui.table
      @file: table_renderer.py
   @created: Tue, 4 May 2021
    @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
      @site: https://github.com/yorevs/hspylib
   @license: MIT - Please refer to <https://opensource.org/licenses/MIT>

   Copyright·(c)·2024,·HSPyLib
"""
from clitt.core.term.screen import Screen
from clitt.core.term.terminal import Terminal
from clitt.core.tui.table.table_enums import TextAlignment, TextCase
from clitt.core.tui.tui_preferences import TUIPreferences
from collections.abc import Iterable as IterableABC
from functools import cached_property, partial, reduce
from hspylib.core.preconditions import check_argument
from hspylib.core.tools.commons import file_is_not_empty
from hspylib.core.tools.text_tools import elide_text, ensure_endswith
from operator import add
from typing import Any, Callable, Iterable, List, Tuple, TypeAlias

import csv
import os

# fmt: off
AlignmentFn : TypeAlias = Callable[[str, int], str]
TestCaseFn  : TypeAlias = Callable[[str], str]
# fmt: on


class TableRenderer:
    """Utility class to render terminal UI tables."""

    DEFAULT_MINIMUM_CELL_SIZE = 6

    @staticmethod
    def import_csv(
        filepath: str, caption: str | None = None, has_headers: bool = True, delimiter: chr = ","
    ) -> "TableRenderer":
        """Render the table based on a CSV file."""
        check_argument(file_is_not_empty(filepath), f"File not found: {filepath}")
        headers, data = None, []
        with open(filepath, encoding="UTF8") as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=delimiter)
            line_count = 0
            for row in csv_reader:
                line_count += 1
                if line_count == 1:
                    if has_headers:
                        headers = row
                        continue
                    headers = [f"C{idx}" for idx, _ in enumerate(row)]
                data.append(row)
        return TableRenderer(headers, data, caption)

    def __init__(self, headers: List[str], data: Iterable, caption: str | None = None):
        """
        :param headers: table headers to be displayed.
        :param data: table record set with the selected rows.
        :param caption: table caption to be displayed.
        """

        self._terminal: Terminal = Terminal.INSTANCE
        self._headers: List[str] = headers
        self._data: List[Any] = data if data else []
        self._caption: str = caption
        self._columns: range = range(self.columns)
        self._min_cell_size: int = self.DEFAULT_MINIMUM_CELL_SIZE
        self._header_alignment: TextAlignment = TextAlignment.CENTER
        self._cell_alignment: TextAlignment = TextAlignment.LEFT
        self._header_case: TextCase = TextCase.UPPER
        self._adjust_cells = None

        check_argument(self.columns >= 1, "Headers are required")
        self._cell_sizes = [0 for _ in range(self.columns)]
        self.adjust_cells_auto()
        if data:
            c_len = len(min(data, key=len))
            check_argument(
                c_len == self.columns, "Headers and Columns must have the same size: {} vs {}", c_len, self.columns
            )
            self._footer = f":: Displaying {c_len} of {c_len} records"
        else:
            self._footer = ":: No data to display"

    @property
    def terminal(self) -> Terminal:
        return self._terminal

    @property
    def screen(self) -> Screen:
        return self.terminal.screen

    @property
    def prefs(self) -> TUIPreferences:
        return self.screen.preferences

    @property
    def column_sizes(self) -> List[int]:
        return self._cell_sizes

    @cached_property
    def columns(self) -> int:
        return len(self.headers)

    @property
    def cell_alignment(self) -> AlignmentFn:
        return self._cell_alignment.val()

    @property
    def header_alignment(self) -> AlignmentFn:
        return self._header_alignment.val()

    @property
    def header_case(self) -> TestCaseFn:
        return self._header_case.val()

    @property
    def caption(self) -> str:
        return self._caption

    @property
    def footer(self) -> str:
        return self._footer

    @footer.setter
    def footer(self, other: str) -> None:
        self._footer = other

    @property
    def data(self) -> Iterable:
        return self._data

    @property
    def headers(self) -> List[str]:
        return self._headers

    def set_header_alignment(self, alignment: TextAlignment) -> None:
        """Set table headers alignment.
        :param alignment: table header text alignment function.
        :return None
        """
        self._header_alignment = alignment

    def set_header_case(self, test_case: TextCase) -> None:
        """Set table headers alignment.
        :param test_case: table header text case function.
        :return None
        """
        self._header_case = test_case

    def set_cell_alignment(self, alignment: TextAlignment) -> None:
        """Set table cell alignment.
        :param alignment: table cell text alignment function.
        :return None
        """
        self._cell_alignment = alignment

    def set_cell_sizes(self, *sizes: int) -> None:
        """Render table based on a list of fixed sizes.
        :param sizes: the list of specific cell sizes.
        :return None
        """
        if len(sizes) == 1 and isinstance(sizes[0], IterableABC) and not isinstance(sizes[0], (str, bytes)):
            sizes = tuple(int(size) for size in sizes[0])
        else:
            sizes = tuple(int(size) for size in sizes)
        if not sizes:
            return
        max_cell_size = self.screen.columns if self._fits(sizes) else int(self.screen.columns / self.columns)
        for idx, size in enumerate(sizes[: self.columns]):
            self._cell_sizes[idx] = min(max_cell_size, max(self._min_cell_size, size))

    def set_min_cell_size(self, size: int) -> None:
        """Set the minimum length of a cell.
        :param size: minimum table cell size.
        :return None
        """
        self._min_cell_size = max(self.DEFAULT_MINIMUM_CELL_SIZE, size)
        self.set_cell_sizes(*(max(self._cell_sizes[idx], size) for idx, _ in enumerate(self.headers)))

    def adjust_cells_by_headers(self) -> None:
        """Adjust cell sizes based on the column header length.
        :return None
        """
        args = [max(self._min_cell_size, len(header)) for header in self.headers]
        self._adjust_cells = partial(self.set_cell_sizes, args)

    def adjust_cells_by_largest_header(self) -> None:
        """Adjust cell sizes based on the maximum length of a header.
        :return None
        """
        max_len = len(max(self.headers))
        args = [max(self._min_cell_size, max_len) for _ in self.headers]
        self._adjust_cells = partial(self.set_cell_sizes, args)

    def adjust_cells_by_largest_cell(self) -> None:
        """Adjust cell sizes based on the maximum length of a cell.
        :return None
        """
        max_len = 0
        for row in self.data:
            max_len = max(max_len, len(max(list(map(str, row)), key=len)))
        args = [max_len for _ in self.headers]
        self._adjust_cells = partial(self.set_cell_sizes, args)

    def adjust_cells_by_fixed_size(self, size: int) -> None:
        """Adjust cell sizes to a fixed size.
        :param size: the fixed cell size.
        :return None
        """
        args = [size for _ in self.headers]
        self._adjust_cells = partial(self.set_cell_sizes, args)

    def adjust_cells_to_fit_screen(self) -> None:
        """Adjust cell sizes accordingly to fill the screen size
        :return None
        """
        distributed_size = int(self.screen.columns / self.columns) - 3
        self.adjust_cells_by_fixed_size(distributed_size)

    def adjust_cells_auto(self) -> None:
        """Ensure all cells and headers are visible with the minimum size possible.
        :return None
        """
        if not self.data:
            self.adjust_cells_by_headers()
        else:
            sizes = self._cell_sizes
            for cell, c_size in zip(self.data, sizes):
                sizes = [
                    max(len(self.headers[idx]), max(sizes[idx], max(c_size, len(str(cell[idx])))))
                    for idx, _ in enumerate(self.headers)
                ]
            args = [size for size in sizes]
            self._adjust_cells = partial(self.set_cell_sizes, args)

    def render(self) -> None:
        """Render the table.
        :return None
        """
        self._adjust_cells()
        header_line, data_lines = self._format_header_row(), self._format_data_rows()
        table_line = "+" + "+".join(f"{'-' * (self._cell_sizes[idx] + 2)}" for idx in self._columns) + "+"
        self._render_table(table_line, header_line, data_lines)

    def export_csv(self, filepath: str, delimiter: chr = ",", has_headers: bool = True) -> None:
        """Export the table to CSV format.
        :return None
        """
        csv_file = ensure_endswith(filepath, ".csv")
        with open(csv_file, "w", encoding="UTF8") as csv_file:
            writer = csv.writer(csv_file, delimiter=delimiter)
            if has_headers:
                writer.writerow(self.headers)
            writer.writerows(self.data)

    def _format_header_row(self) -> str:
        """Format the table header using the defined preferences.
        :return the formatted header row.
        """
        header_cols = [self.header_alignment(self._header_text(idx), self._cell_sizes[idx]) for idx in self._columns]
        return f"| {' | '.join(header_cols)} |"

    def _format_data_rows(self) -> List[str]:
        """Format the table rows using the defined preferences.
        :return a list containing the formatted data rows.
        """
        # fmt: off
        return [
            "| " +
            ' | '.join(
                f"{self.cell_alignment(self._cell_text(row, column), self._cell_sizes[column])}"
                for column in self._columns
            ) +
            " |" for row in self.data
        ]
        # fmt: on

    def _display_data(self, data: Any, end: str = os.linesep) -> None:
        """Display data on the screen.
        :param data the data to be printed.
        :param end the terminating string.
        :return None
        """
        self.terminal.cursor.write(data, end)

    def _fits(self, sizes: Tuple[int, ...]) -> bool:
        """Return whether the expected table size fits the screen or not.
        :param sizes the expected sizes to check.
        :return True if the table fits the screen; False otherwise.
        """
        extra_len = 4 + ((self.columns - 1) * 3)  # 4 for '|  |' and 3 for each '-+-'
        exp_table_size = reduce(add, sizes) + extra_len
        return exp_table_size < self.screen.columns

    def _header_text(self, column: int) -> str:
        """Return a header for the specified column.
        :param column the specified table column.
        :return the header text at (row, column).
        """
        return self.header_case(elide_text(self.headers[column], self._cell_size(column)))

    def _cell_text(self, row: tuple, column: int) -> str:
        """Return a text for the specified cell (row, column).
        :param row the specified table row.
        :param column the specified table column.
        :return the cell text at (row, column).
        """
        return elide_text(str(row[column]), self._cell_size(column))

    def _cell_size(self, column: int) -> int:
        """Return the size of the specified column.
        :param column the specified table column.
        :return the cell size at (row, column).
        """
        return self._cell_sizes[column]

    def _render_table(self, table_line: str, header_line: str, data_rows: List[str]) -> None:
        """Renders the table data.
        :param table_line: a formatted line composed by all columns.
        :param header_line: a formatted line composed by the table header.
        :param data_rows: the formatted table data rows.
        :return None
        """
        magic_num = 4  # this is the length of the starting and ending characters: '|  |'
        line_length, render_line = len(table_line) - magic_num, f"+{table_line[1:-1]}+"
        self._display_data("")
        if self.caption:
            border_line = render_line.replace("+", "-")
            self._display_data(border_line)
            self._display_data("| " + self.prefs.caption_color.placeholder, end="")
            self._display_data(f"{elide_text(self.caption, line_length): ^{line_length}}", end="")
            self._display_data("%NC%" + " |")
        self._display_data(render_line)
        self._display_data(header_line)
        self._display_data(render_line)
        self._display_data(os.linesep.join(data_rows) if data_rows else f"| {'<empty>': ^{line_length}} |")
        self._display_data(render_line)
        if self.footer:
            self._display_data(self.footer)
