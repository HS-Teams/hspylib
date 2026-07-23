#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Hqt
@package: hqt.promotions
   @file: hlabel.py
@created: Tue, 4 May 2021
 @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: https://github.com/yorevs/hspylib
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFontMetrics, QMouseEvent, QResizeEvent, QTextDocument
from PyQt6.QtWidgets import QLabel, QSizePolicy, QWidget
from typing import Optional


class HLabel(QLabel):
    """TODO"""

    clicked = pyqtSignal()
    elisionChanged = pyqtSignal()

    def __init__(self, parent: Optional[QWidget]):
        super().__init__(parent)
        self._clickable = False
        self._elidable = True
        self._dynamic_tooltip = False
        self._content = self.text()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def elidable(self) -> bool:
        return self._elidable

    def set_elidable(self, elidable: bool) -> None:
        self._elidable = elidable

    def clickable(self) -> bool:
        return self._clickable

    def set_clickable(self, clickable: bool) -> None:
        self._clickable = clickable
        self.setCursor(
            Qt.CursorShape.PointingHandCursor
            if clickable
            else Qt.CursorShape.ArrowCursor
        )

    def dynamic_tooltip(self) -> bool:
        return self._dynamic_tooltip

    def set_dynamic_tooltip(self, dynamic_tooltip: bool) -> None:
        self._dynamic_tooltip = dynamic_tooltip

    def mousePressEvent(self, ev: Optional[QMouseEvent]) -> None:
        if self._clickable:
            self.clicked.emit()
        super().mousePressEvent(ev)

    def setText(self, text: Optional[str]) -> None:
        text = text or ""
        self._content = text
        if not self.toolTip() or self._dynamic_tooltip:
            self.setToolTip(text)
        if self._elidable:
            metrics = QFontMetrics(self.font())
            max_length = int(self.width() / max(1, metrics.horizontalAdvance("M")))
            doc = QTextDocument()
            doc.setHtml(text)
            plain_text = doc.toPlainText()
            if len(plain_text) > max_length:
                self.elisionChanged.emit()
                elided_last_line = metrics.elidedText(
                    text, Qt.TextElideMode.ElideRight, self.width()
                )
                super().setText(elided_last_line)
                return
        super().setText(text)

    def resizeEvent(self, event: Optional[QResizeEvent]) -> None:
        if self._content and self._content != self.text():
            self.setText(self._content)
        super().resizeEvent(event)
