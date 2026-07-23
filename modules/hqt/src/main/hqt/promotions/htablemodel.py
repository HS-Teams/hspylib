#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Hqt
@package: hqt.promotions
   @file: htablemodel.py
@created: Tue, 4 May 2021
 @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: https://github.com/yorevs/hspylib
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from hspylib.core.collection_filter import CollectionFilter, FilterCondition
from hspylib.core.tools.commons import class_attribute_names, class_attribute_values
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QTableView
from typing import Any, Deque, Generic, List, Optional, Tuple, Type, TypeVar, Union

import collections

T = TypeVar("T")


class HTableModel(QAbstractTableModel, Generic[T]):
    """TODO"""

    def __init__(
        self,
        parent: QTableView,
        clazz: Type[Any],
        headers: Optional[List[str]] = None,
        table_data: Optional[List[T]] = None,
        cell_alignments: Optional[List[Qt.AlignmentFlag]] = None,
        max_rows: int = 500,
    ):
        QAbstractTableModel.__init__(self, parent)
        self._parent = parent
        self._clazz = clazz
        self._max_rows = max_rows
        self._data: Deque[T] = collections.deque(maxlen=max_rows)
        self._filters = CollectionFilter()
        self._headers = headers or self._headers_by_entity()
        self._cell_alignments = cell_alignments
        self._parent.setModel(self)
        self.push_data(table_data or [])

    def removeRow(
        self, row: int, parent: QModelIndex = QModelIndex()
    ) -> bool:  # pylint: disable=unused-argument
        """TODO"""
        if 0 <= row < len(self._data):
            self.beginRemoveRows(QModelIndex(), row, row)
            del self._data[row]
            self.endRemoveRows()
            return True
        return False

    def data(
        self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)
    ) -> Any:
        """TODO"""
        if not index.isValid() or not 0 <= index.row() < len(self._data):
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            row_dict = self._data[index.row()].__dict__
            value = class_attribute_values(row_dict)[index.column()]
            return str(value if value is not None else "")
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return (
                self._cell_alignments[index.column()]
                if self._cell_alignments
                else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
        if role == Qt.ItemDataRole.BackgroundRole and index.row() % 2 != 0:
            return self._parent.palette().color(QPalette.ColorRole.Window).lighter(100)
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = int(Qt.ItemDataRole.DisplayRole),
    ) -> Any:
        """TODO"""
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return (
                self._headers[section].upper() if section < len(self._headers) else "-"
            )
        if orientation == Qt.Orientation.Vertical:
            return str(section)
        return None

    def rowCount(
        self, parent: QModelIndex = QModelIndex()
    ) -> int:  # pylint: disable=unused-argument
        """TODO"""
        return len(self._data) if self._data else 0

    def columnCount(
        self, parent: QModelIndex = QModelIndex()
    ) -> int:  # pylint: disable=unused-argument
        """TODO"""
        return len(self._headers)

    def sort(
        self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder
    ) -> None:
        """TODO"""
        keys = class_attribute_names(self._clazz)
        self.layoutAboutToBeChanged.emit()
        values = sorted(
            self._data,
            key=lambda x: getattr(x, keys[column]),
            reverse=order == Qt.SortOrder.DescendingOrder,
        )
        self._data = collections.deque(values, maxlen=self._max_rows)
        self.layoutChanged.emit()

    def append(self, data: T):
        """TODO"""
        if data and not self._filters.should_filter(data):
            if len(self._data) == self._max_rows:
                self.beginResetModel()
                self._data.append(data)
                self.endResetModel()
                return
            row = self.rowCount()
            self.beginInsertRows(QModelIndex(), row, row)
            self._data.append(data)
            self.endInsertRows()

    def apply_filter(
        self,
        name: str,
        el_name: str,
        condition: FilterCondition,
        el_value: Union[int, str, bool, float],
    ) -> None:
        """TODO"""
        self._filters.apply_filter(name, el_name, condition, el_value)

    def filter(self) -> None:
        """TODO"""
        self.beginResetModel()
        self._data = collections.deque(
            self._filters.filter(list(self._data)), maxlen=self._max_rows
        )
        self.endResetModel()

    def row(self, index: QModelIndex) -> T:
        """TODO"""
        return self._data[index.row()]

    def column(self, index: QModelIndex) -> Any:
        """TODO"""
        row = self.row(index)
        col_name = str(list(vars(row))[index.column()])
        return getattr(row, col_name)

    def push_data(self, data: Union[List[T], T]) -> None:
        """TODO"""
        if data:
            if isinstance(data, list):
                list(map(self.append, data))
            else:
                self.append(data)
            self.layoutChanged.emit()

    def clear(self):
        """TODO"""
        self.beginResetModel()
        self._data.clear()
        self.endResetModel()

    def is_empty(self) -> bool:
        """TODO"""
        return len(self._data) == 0

    def refresh_data(self) -> None:
        """TODO"""
        self.filter()

    def remove_rows(self, rows: List[QModelIndex]):
        """TODO"""
        # Because we are using deque, we need to sort DESC to avoid deleting wrong indexes
        for row in sorted(rows, key=lambda index: index.row(), reverse=True):
            self.removeRow(row.row())

    def _headers_by_entity(self) -> List[str]:
        """TODO"""
        attributes = class_attribute_names(self._clazz)
        return [str(x).capitalize() for x in attributes]

    def selected_data(self) -> Tuple[List[QModelIndex], List[T]]:
        """TODO"""
        sel_model = self._parent.selectionModel()
        if sel_model:
            sel_indexes = sel_model.selectedIndexes()
            sel_rows = sorted({idx.row() for idx in sel_indexes})
            return sel_indexes, [self._data[row] for row in sel_rows]
        return [], []

    def filters(self) -> CollectionFilter:
        """TODO"""
        return self._filters
