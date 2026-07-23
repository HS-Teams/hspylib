#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Qt6 regression tests for the shared HQT widgets."""

from __future__ import annotations

import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from calculator.views.main_qt_view import MainQtView as CalculatorView
from hqt.promotions.hcombobox import HComboBox
from hqt.promotions.hconsole import HConsole
from hqt.promotions.hframe import HFrame
from hqt.promotions.hlabel import HLabel
from hqt.promotions.hlistwidget import HListWidget
from hqt.promotions.hstacked_widget import HStackedWidget
from hqt.promotions.htablemodel import HTableModel
from hqt.promotions.htableview import HTableView
from hqt.promotions.htoolbox import HToolBox
from hqt.views.qt_view import QtView
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QLabel, QWidget

FORMS = Path(__file__).parents[1] / "demo" / "calculator" / "resources" / "forms"


class Row:
    def __init__(self, name: str, amount: int):
        self.name = name
        self.amount = amount


class Qt6WidgetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_promoted_widgets_construct_with_pyqt6(self) -> None:
        widgets = [
            HComboBox(),
            HConsole(None),
            HFrame(),
            HLabel(None),
            HListWidget(),
            HStackedWidget(),
            HTableView(None),
            HToolBox(),
        ]
        self.assertTrue(
            all(widget.__class__.__module__.startswith("hqt.") for widget in widgets)
        )

    def test_list_widget_uses_qt6_item_flags(self) -> None:
        widget = HListWidget()
        widget.set_item("one")
        widget.set_item("two")
        widget.set_editable(False)
        self.assertEqual(["one", "two"], widget.as_list())
        self.assertEqual(1, widget.index_of("two"))
        self.assertFalse(bool(widget.item(0).flags() & Qt.ItemFlag.ItemIsEditable))

    def test_console_uses_qt6_text_and_palette_apis(self) -> None:
        console = HConsole(None)
        console.set_show_line_numbers(True)
        console.set_highlight_enable(True)
        console.set_plain_text("first\nsecond")
        console.highlight_current_line()
        self.assertGreater(console.line_number_area_width(), 0)

    def test_table_model_returns_native_qt6_role_values(self) -> None:
        view = HTableView(None)
        model = HTableModel(view, Row)
        model.append(Row("first", 3))
        index = model.index(0, 0)
        self.assertEqual("first", model.data(index, int(Qt.ItemDataRole.DisplayRole)))
        self.assertEqual(2, model.columnCount())
        self.assertTrue(model.removeRow(0))
        self.assertEqual(0, model.rowCount())

    def test_stacked_widget_animation_uses_qt6_animation_api(self) -> None:
        stack = HStackedWidget()
        stack.resize(200, 100)
        stack.addWidget(QLabel("one"))
        stack.addWidget(QLabel("two"))
        stack.set_speed(1)
        stack.show()
        stack.slide_to_index(1)
        QTest.qWait(20)
        self.app.processEvents()
        self.assertEqual(1, stack.currentIndex())

    def test_toolbox_and_ui_loader_construct_qt6_forms(self) -> None:
        toolbox = HToolBox()
        toolbox.resize(240, 300)
        toolbox.addItem(QWidget(), "one")
        toolbox.addItem(QWidget(), "two")
        toolbox.setCurrentIndex(1, now=True)
        self.assertEqual(1, toolbox.currentIndex())

        view = QtView("qt_calculator.ui", str(FORMS))
        self.assertIsInstance(view.ui.frameMain, HFrame)

        calculator = CalculatorView()
        calculator._display("12")
        self.assertEqual(12.0, calculator.ui.lcdDisplay.value())


if __name__ == "__main__":
    unittest.main(verbosity=2)
