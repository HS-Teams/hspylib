#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Hqt
@package: hqt.promotions
   @file: hconsole.py
@created: Wed, 30 Jun 2021
 @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: https://github.com/yorevs/hspylib
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from PyQt6.QtCore import QRect, QSize, Qt
from PyQt6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QPainter,
    QPaintEvent,
    QPalette,
    QResizeEvent,
    QTextCursor,
    QTextFormat,
)
from PyQt6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget
from typing import Optional


class HConsole(QPlainTextEdit):
    """TODO"""

    class _LineNumberArea(QWidget):
        """TODO"""

        def __init__(self, text_edit: "HConsole"):
            super().__init__(text_edit)
            self._text_edit = text_edit

        def sizeHint(self) -> QSize:
            return QSize(self._text_edit.line_number_area_width(), 0)

        def paintEvent(self, event: Optional[QPaintEvent]) -> None:
            if event is not None:
                self._text_edit.line_number_area_paint_event(event)

    def __init__(self, parent: Optional[QWidget], max_lines: int = 1000):
        super().__init__(parent)
        self._max_lines = max_lines

        # Defaults
        self._context_menu_enable = True
        self._clearable = True
        self._highlight_enabled = False
        self._show_line_numbers = False
        self.setReadOnly(True)
        self.setPlaceholderText("No messages received yet")
        self.setFont(QFont("Courier New", 14))
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)

        # Create line numbers widget
        self._line_number_area = self._LineNumberArea(self)
        document = self.document()
        if document is not None:
            document.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.update_line_number_area_width()
        self.highlight_current_line()

    def resizeEvent(self, event: Optional[QResizeEvent]) -> None:
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def line_number_area_paint_event(self, event: QPaintEvent) -> None:
        """Paint the numbers of the line number area"""
        margin_right = -2
        bg_color = self.palette().color(QPalette.ColorRole.Window).lighter(100)
        txt_color = self.palette().color(QPalette.ColorRole.WindowText).darker(160)
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), bg_color)
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(
            self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        )
        bottom = top + round(self.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(txt_color)
                painter.drawText(
                    margin_right,
                    top,
                    self._line_number_area.width(),
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    number,
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

    def line_number_area_width(self) -> int:
        """Return the current line number area width"""
        if self._show_line_numbers:
            digits = 1
            margin_left = 10
            document = self.document()
            max_count = max(1, document.blockCount() if document is not None else 0)
            char_width = self.fontMetrics().horizontalAdvance("_")
            # Check the amount of digits to be printed
            while max_count >= 10:
                max_count //= 10
                digits += 1

            return margin_left + char_width * digits

        return 0

    def highlight_current_line(self) -> None:
        """Highlight current line number if highlighting is enabled"""
        if self._highlight_enabled and self.line_count() > 1:
            bg = self.palette().color(QPalette.ColorRole.Window).lighter(120)
            bg.setAlphaF(0.6)
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(bg)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            self.setExtraSelections([selection])

    def update_line_number_area_width(
        self, new_block_count: int = 0
    ) -> None:  # pylint: disable=unused-argument
        """Update the line number area width"""
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect: QRect, dy: int):
        """Update the line number area rect"""
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(
                0, rect.y(), self._line_number_area.width(), rect.height()
            )
        viewport = self.viewport()
        if viewport is not None and rect.contains(viewport.rect()):
            self.update_line_number_area_width()

    def line_count(self) -> int:
        """Return the number of lines the console contains"""
        document = self.document()
        return document.blockCount() if document is not None else 0

    def is_empty(self) -> bool:
        """Return true if console has no lines"""
        return self.line_count() == 0

    def set_plain_text(self, text: str) -> None:
        document = self.document()
        if document is not None:
            document.setPlainText(text)

    def set_html_text(self, text: str) -> None:
        document = self.document()
        if document is not None:
            document.setHtml(text)

    def push_text(self, text: str, color: Optional[QColor] = None) -> None:
        """Push text to the console. If the maximum buffer size reached then lines are erased from the top"""
        fmt_text = f"<font color={color.name() if color else '#FFFFFF'}>{text}</font>"
        if self.line_count() + 1 > self._max_lines:
            self.pop_text()
        self.appendHtml(fmt_text)

    def pop_text(self, count: int = 0) -> str:
        """Pop <count> lines form the top->bottom"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        cursor.movePosition(
            QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.MoveAnchor, count
        )
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        selected_text = cursor.selectedText()
        cursor.removeSelectedText()
        cursor.deleteChar()
        self.setTextCursor(cursor)

        return selected_text

    def _context_menu(self) -> None:
        """Display the custom context menu"""
        if self._context_menu_enable:
            ctx_menu = self.createStandardContextMenu()
            if ctx_menu is not None:
                if self._clearable:
                    ctx_menu.addSeparator()
                    ctx_menu.addAction("Clear", self.clear)
                ctx_menu.exec(QCursor.pos())

    def set_context_menu_enable(self, enabled: bool = True):
        """Whether context menu is enabled or not"""
        self._context_menu_enable = enabled

    def set_clearable(self, clearable: bool = True):
        """Whether the widget is clearable or not"""
        self._clearable = clearable

    def set_highlight_enable(self, enabled: bool = True):
        """Whether line highlight is enabled or not"""
        self._highlight_enabled = enabled

    def set_show_line_numbers(self, show: bool = True):
        """Whether to show line numbers or not"""
        self._show_line_numbers = show
        self.update_line_number_area_width()
