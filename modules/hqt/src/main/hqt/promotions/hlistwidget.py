#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Hqt
@package: hqt.promotions
   @file: hlistwidget.py
@created: Tue, 4 May 2021
 @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: https://github.com/yorevs/hspylib
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from hspylib.core.preconditions import check_argument, check_not_none, check_state
from PyQt6.QtCore import pyqtSignal, QModelIndex, Qt
from PyQt6.QtGui import QCursor, QKeyEvent
from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QMenu, QWidget
from typing import Callable, List, Optional, Tuple, Union, overload


class HListWidget(QListWidget):
    """TODO"""

    keyPressed = pyqtSignal(int)

    @staticmethod
    def unset_flag(flags: Qt.ItemFlag, flag: Qt.ItemFlag) -> Qt.ItemFlag:
        """TODO"""
        return flags & ~flag

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._editable = False
        self._selectable = True
        self._items: List[QListWidgetItem] = []
        self._custom_menu_actions: List[Tuple[str, Callable[[], None], bool]] = []
        self._context_menu_enable = True
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)
        self.itemChanged.connect(self.item_changed)

    def keyPressEvent(self, event: Optional[QKeyEvent]) -> None:
        """Handles and forwards the key press event in the list."""
        super().keyPressEvent(event)
        if event is not None:
            self.keyPressed.emit(int(event.key()))

    def item_changed(self, item: QListWidgetItem):
        """Handles itemChanged event to avoid adding duplicates to the list."""
        existing = self.findItems(item.text(), Qt.MatchFlag.MatchFixedString)
        if len(existing) > 1:
            self.del_item(item)

    @overload
    def addItem(self, item: Optional[QListWidgetItem]) -> None: ...

    @overload
    def addItem(self, item: Optional[str]) -> None: ...

    def addItem(self, item: Optional[Union[str, QListWidgetItem]]) -> None:
        """Adds the specified element to this list regardless if it is present or not."""
        if item is None:
            super().addItem(item)
            return
        if isinstance(item, str):
            item = QListWidgetItem(item)
        prev = self.item(self.count() - 1)
        if prev:
            item.setFlags(prev.flags())
        super().addItem(item)
        self._items.append(item)

    def is_empty(self) -> bool:
        """Returns true if this list contains no elements."""
        return len(self._items) == 0

    def set_item(
        self, item: Union[str, QListWidgetItem], flags: Optional[Qt.ItemFlag] = None
    ) -> None:
        """Adds the specified element to this list if it is not already present."""
        item_text = item if isinstance(item, str) else item.text()
        if not self.findItems(item_text, Qt.MatchFlag.MatchFixedString):
            if isinstance(item, str):
                w_item = QListWidgetItem(item)
                w_item.setFlags(
                    flags
                    or Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsEditable
                    | Qt.ItemFlag.ItemIsEnabled
                )
                self.addItem(w_item)
            else:
                item.setFlags(
                    flags
                    or Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsEditable
                    | Qt.ItemFlag.ItemIsEnabled
                )
                self.addItem(item)

    def remove_item_at_index(self, row: int) -> Optional[QListWidgetItem]:
        """Removes the element at the specified row from this list if it is present."""
        item = self.takeItem(row)
        if item:
            self._items.remove(self._items[row])
        return item

    def del_item(
        self, item_or_index: Union[int, QModelIndex, QListWidgetItem]
    ) -> Optional[QListWidgetItem]:
        """Removes the specified element from this list if it is present."""
        item = None
        if isinstance(item_or_index, int):
            if 0 <= item_or_index < len(self._items):
                item = self.remove_item_at_index(item_or_index)
        elif isinstance(item_or_index, QListWidgetItem):
            index = self.indexFromItem(item_or_index)
            if index.isValid():
                item = self.remove_item_at_index(index.row())
        elif isinstance(item_or_index, QModelIndex):
            item = self.remove_item_at_index(item_or_index.row())

        return item

    def clear(self) -> None:
        """Removes all of the elements from this list."""
        super().clear()
        del self._items[:]

    def item_count(self) -> int:
        """Returns the number of elements in this list."""
        return self.count()

    def index_of(self, item: str) -> int:
        """Returns the index of the first occurrence of the specified element in this list,
        or -1 if this list does not contain the element."""
        return next(
            (index for index, obj in enumerate(self._items) if obj.text() == item), -1
        )

    def as_list(self) -> List[str]:
        """Returns a list containing all items in this list as a string."""
        return list(map(QListWidgetItem.text, self._items))

    def current_text(self) -> str:
        """Returns the current item's text."""
        current = self.currentItem()
        return current.text() if current is not None else ""

    def set_context_menu_enable(self, enabled: bool = True) -> None:
        """Whether context menu is enabled or not"""
        self._context_menu_enable = enabled

    def set_editable(self, editable: bool = True) -> None:
        """Set editable property."""
        for item in self._items:
            flags = item.flags()
            if editable:
                item.setFlags(flags | Qt.ItemFlag.ItemIsEditable)
            else:
                item.setFlags(self.unset_flag(flags, Qt.ItemFlag.ItemIsEditable))
        self._editable = editable

    def set_selectable(self, selectable: bool = True) -> None:
        """Set selectable property."""
        for item in self._items:
            flags = item.flags()
            if selectable:
                item.setFlags(flags | Qt.ItemFlag.ItemIsSelectable)
            else:
                item.setFlags(self.unset_flag(flags, Qt.ItemFlag.ItemIsSelectable))
        self._selectable = selectable

    def _context_menu(self) -> None:
        """Display the custom context menu."""
        if self._context_menu_enable:
            ctx_menu = QMenu(self)
            if self._editable:
                ctx_menu.addAction("Add Item", lambda: self.set_item("<new_item>"))
                if not self.is_empty():
                    ctx_menu.addAction(
                        "Delete Item", lambda: self.del_item(self.currentIndex().row())
                    )
                    ctx_menu.addSeparator()
                    ctx_menu.addAction("Clear list", self.clear)

            for act in self._custom_menu_actions:
                check_not_none(act)
                check_state(len(act) == 3, f"Invalid custom menu action: {act}")
                check_argument(callable(act[1]), "The action must be callable")
                if act[2]:
                    ctx_menu.addSeparator()
                ctx_menu.addAction(act[0], act[1])

            ctx_menu.exec(QCursor.pos())
