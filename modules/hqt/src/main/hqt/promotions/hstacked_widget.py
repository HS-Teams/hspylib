#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Hqt
@package: hqt.promotions
   @file: hstacked_widget.py
@created: Wed, 8 Jun 2022
 @author: "<B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: "https://github.com/yorevs/hspylib")
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from PyQt6.QtCore import (
    pyqtSlot,
    QAbstractAnimation,
    QEasingCurve,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    Qt,
)
from PyQt6.QtWidgets import QStackedWidget, QWidget
from typing import List, Optional


class HStackedWidget(QStackedWidget):
    """TODO"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._slide_direction = Qt.Orientation.Horizontal
        self._slide_speed = 500
        self._animation_type = QEasingCurve.Type.OutCubic
        self._cur_idx = 0
        self._next_idx = 0
        self._wrap = False
        self._pos_current = QPoint(0, 0)
        self._widgets: List[QWidget] = []
        self._active = False

    def set_direction(self, direction) -> None:
        """TODO"""
        self._slide_direction = direction

    def set_speed(self, speed) -> None:
        """TODO"""
        self._slide_speed = speed

    def set_animation(self, animation_type) -> None:
        """TODO"""
        self._animation_type = animation_type

    def set_wrap(self, wrap) -> None:
        """TODO"""
        self._wrap = wrap

    def widgets(self) -> List[QWidget]:
        """TODO"""
        return self._widgets

    def addWidget(self, widget: Optional[QWidget]) -> int:
        """TODO"""
        index = super().addWidget(widget)
        if widget is not None and index >= 0:
            self._widgets.append(widget)
        return index

    @pyqtSlot()
    def slide_previous(self) -> None:
        """TODO"""
        now = self.currentIndex()
        if self._wrap or now > 0:
            self.slide_to_index(now - 1)

    @pyqtSlot()
    def slide_next(self) -> None:
        """TODO"""
        now = self.currentIndex()
        if self._wrap or now < (self.count() - 1):
            self.slide_to_index(now + 1)

    @pyqtSlot(int)
    def slide_to_index(self, idx: int) -> None:
        """TODO"""
        if self.count() == 0:
            return
        if idx != 0:
            if idx > (self.count() - 1):
                idx %= self.count()
            elif idx < 0:
                idx = (idx + self.count()) % self.count()
        widget = self.widget(idx)
        if widget is not None:
            self._slide_to_widget(widget)

    def _slide_to_widget(self, widget: QWidget) -> None:
        """TODO"""
        if self._active:
            return

        self._active = True
        idx = self.currentIndex()
        next_idx = self.indexOf(widget)

        if idx == next_idx:
            self._active = False
            return

        offset_x, offset_y = self.frameRect().width(), self.frameRect().height()
        current_widget = self.widget(idx)
        next_widget = self.widget(next_idx)
        if current_widget is None or next_widget is None:
            self._active = False
            return
        next_widget.setGeometry(self.frameRect())

        if self._slide_direction == Qt.Orientation.Vertical:
            if idx < next_idx:
                offset_x, offset_y = 0, -offset_y
            else:
                offset_x = 0
        else:
            if idx < next_idx:
                offset_x, offset_y = -offset_x, 0
            else:
                offset_y = 0

        pos_next = next_widget.pos()
        pos_current = current_widget.pos()
        self._pos_current = pos_current
        offset = QPoint(offset_x, offset_y)
        next_widget.move(pos_next - offset)
        next_widget.show()
        next_widget.raise_()

        anim_group = QParallelAnimationGroup(self)
        anim_group.finished.connect(self.animation_done)

        for index, start, end in zip(
            (idx, next_idx),
            (pos_current, pos_next - offset),
            (pos_current + offset, pos_next),
        ):
            animated_widget = self.widget(index)
            if animated_widget is None:
                continue
            animation = QPropertyAnimation(animated_widget, b"pos", anim_group)
            animation.setDuration(self._slide_speed)
            animation.setEasingCurve(self._animation_type)
            animation.setStartValue(start)
            animation.setEndValue(end)
            anim_group.addAnimation(animation)

        self._next_idx = next_idx
        self._cur_idx = idx
        self._active = True
        anim_group.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    @pyqtSlot()
    def animation_done(self) -> None:
        """TODO"""
        current_widget = self.widget(self._cur_idx)
        if current_widget is not None:
            current_widget.hide()
            current_widget.move(self._pos_current)
        self._active = False
        self.setCurrentIndex(self._next_idx)
