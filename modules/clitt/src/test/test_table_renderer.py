#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

from _test_setup import setup_test_environment

setup_test_environment()

from clitt.core.term.terminal import Terminal
from clitt.core.tui.table.table_enums import TextAlignment, TextCase
from clitt.core.tui.table.table_renderer import TableRenderer


class TableRendererTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.terminal = Terminal.INSTANCE or Terminal()
        screen = self.terminal.screen
        screen.columns = 80
        screen.preferences = SimpleNamespace(
            caption_color=SimpleNamespace(placeholder="%CAP%")
        )
        if not hasattr(screen, "cursor") or not hasattr(screen.cursor, "write"):
            screen.cursor = SimpleNamespace(write=lambda *_, **__: None)

    def tearDown(self) -> None:
        self.terminal.screen.columns = 80

    def create_renderer(self, headers, data=None, caption=None) -> TableRenderer:
        return TableRenderer(headers, data or [], caption)


class TestTableRendererImportCsv(TableRendererTestCase):
    def test_import_csv_with_headers_and_caption(self):
        with tempfile.NamedTemporaryFile("w", newline="", delete=False) as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["Name", "Age"])
            writer.writerow(["Alice", "30"])
            writer.writerow(["Bob", "25"])
            csv_path = csv_file.name

        try:
            renderer = TableRenderer.import_csv(csv_path, caption="People", has_headers=True)

            self.assertEqual(["Name", "Age"], renderer.headers)
            self.assertEqual([["Alice", "30"], ["Bob", "25"]], renderer.data)
            self.assertEqual("People", renderer.caption)
            self.assertEqual(":: Displaying 2 of 2 records", renderer.footer)
        finally:
            Path(csv_path).unlink(missing_ok=True)

    def test_import_csv_without_headers_infers_defaults(self):
        with tempfile.NamedTemporaryFile("w", newline="", delete=False) as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["alpha", "beta", "gamma"])
            writer.writerow(["delta", "epsilon", "zeta"])
            csv_path = csv_file.name

        try:
            renderer = TableRenderer.import_csv(csv_path, caption=None, has_headers=False)

            self.assertEqual(["C0", "C1", "C2"], renderer.headers)
            self.assertEqual(
                [["alpha", "beta", "gamma"], ["delta", "epsilon", "zeta"]],
                renderer.data,
            )
        finally:
            Path(csv_path).unlink(missing_ok=True)


class TestTableRendererSizing(TableRendererTestCase):
    def test_adjustment_helpers_apply_expected_sizes(self):
        renderer = self.create_renderer(
            ["First", "Second"],
            [["short", "cells"], ["this is the longest value", "tiny"]],
        )

        renderer.adjust_cells_by_headers()
        renderer._adjust_cells()
        self.assertEqual([6, 6], renderer.column_sizes)

        renderer.adjust_cells_by_largest_cell()
        renderer._adjust_cells()
        self.assertEqual([len("this is the longest value")] * 2, renderer.column_sizes)

    def test_set_cell_sizes_and_minimum_respect_screen_bounds(self):
        renderer = self.create_renderer(["Col1", "Col2"], [["1", "2"]])
        renderer.screen.columns = 40

        renderer.set_cell_sizes((30, 30))
        self.assertEqual([20, 20], renderer.column_sizes)

        renderer.screen.columns = 80
        renderer.set_cell_sizes((8, 9))
        renderer.set_min_cell_size(12)
        self.assertEqual([12, 12], renderer.column_sizes)


class TestTableRendererPreferences(TableRendererTestCase):
    def test_alignment_and_case_setters_update_rendering_functions(self):
        renderer = self.create_renderer(["Header"], [["value"]])

        renderer.set_header_alignment(TextAlignment.LEFT)
        renderer.set_cell_alignment(TextAlignment.RIGHT)
        renderer.set_header_case(TextCase.LOWER)

        self.assertIs(renderer.header_alignment, TextAlignment.LEFT.val())
        self.assertIs(renderer.cell_alignment, TextAlignment.RIGHT.val())
        self.assertIs(renderer.header_case, TextCase.LOWER.val())

    def test_footer_reflects_available_data(self):
        renderer = self.create_renderer(["H1", "H2", "H3"], [["a", "b", "c"]])

        self.assertEqual(":: Displaying 3 of 3 records", renderer.footer)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
