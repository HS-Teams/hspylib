#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Kafman
@package: kafman.views.dialogs
   @file: settings_dialog.py
@created: Wed, 8 Jun 2022
 @author: "<B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: "https://github.com/yorevs/hspylib")
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from hqt.promotions.hlistwidget import HListWidget
from hspylib.core.config.parser_factory import ParserFactory
from hspylib.core.enums.charset import Charset
from hspylib.core.enums.enumeration import Enumeration
from hspylib.core.preconditions import check_not_none
from kafman.__classpath__ import classpath
from PyQt6 import uic
from PyQt6.QtCore import QObject, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QDialogButtonBox, QWidget
from io import StringIO
from typing import Any, Dict


class SettingsDialog(QObject):
    """TODO"""

    DIALOG_FORM = classpath.get_resource("forms/settings_dlg.ui")

    # fmt: off
    FORBIDDEN_SETTINGS = {
        'key.deserializer': '', 'value.deserializer': '',
        'key.serializer': '', 'value.serializer': ''
    }
    # fmt: on

    class SettingsType(Enumeration):
        """TODO"""

        PRODUCER_SETTINGS = classpath.get_resource(
            "producer-settings.properties"
        ).read_text(encoding=Charset.UTF_8.val)
        CONSUMER_SETTINGS = classpath.get_resource(
            "consumer-settings.properties"
        ).read_text(encoding=Charset.UTF_8.val)

        # fmt: off
        PRODUCER = 'PRODUCER', PRODUCER_SETTINGS
        CONSUMER = 'CONSUMER', CONSUMER_SETTINGS
        # fmt: on

        def settings(self) -> str:
            return self.value[1]

    def __init__(
        self,
        parent: QWidget,
        settings_type: "SettingsType",
        current_settings: Dict[str, Any],
        settings_widget: HListWidget,
    ):
        super().__init__(parent)
        ui_class, base_class = uic.loadUiType(self.DIALOG_FORM)
        check_not_none((ui_class, base_class))
        self.dialog, self.ui = base_class(parent), ui_class()
        self.ui.setupUi(self.dialog)
        self._settings: Dict[str, Any] = {}
        self._settings_type = settings_type
        self._current_settings = current_settings
        self._forbidden_settings = set(current_settings) | set(self.FORBIDDEN_SETTINGS)
        self._settings_widget = settings_widget
        self._setup_controls()

    def _setup_controls(self) -> None:
        """TODO"""
        self.dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.dialog.setModal(True)
        self._set_font()
        self.ui.cmb_settings.currentTextChanged.connect(self._change_setting)
        self.ui.btn_box.clicked.connect(self._button_clicked)
        self._fill_settings()

    def _set_font(self) -> None:
        """TODO"""
        widgets = list(
            filter(lambda o: hasattr(getattr(self.ui, o), "setFont"), vars(self.ui))
        )
        list(
            map(
                lambda w: getattr(self.ui, w).setFont(
                    QFont("DroidSansMono Nerd Font", 13)
                ),
                widgets,
            )
        )

    def set_window_title(self, param):
        """TODO"""
        self.dialog.setWindowTitle(param)

    def show(self) -> None:
        """TODO"""
        self.dialog.exec()

    def _button_clicked(self, button) -> None:
        """TODO"""
        role = self.ui.btn_box.buttonRole(button)
        if role == QDialogButtonBox.ButtonRole.ApplyRole:
            self._add_setting()

    def _fill_settings(self) -> None:
        """TODO"""
        parser = ParserFactory.create(".properties")
        self._settings.update(parser.parse(StringIO(self._settings_type.settings())))
        self.ui.cmb_settings.addItems(
            {
                k: v
                for (k, v) in self._settings.items()
                if k not in self._forbidden_settings
            }
        )

    def _change_setting(self, setting_name: str) -> None:
        """TODO"""
        self.ui.le_value.setText(self._settings.get(setting_name, ""))

    def _add_setting(self) -> None:
        """TODO"""
        setting_name = self.ui.cmb_settings.currentText()
        if not setting_name:
            return
        setting_value = self.ui.le_value.text()
        self._settings_widget.set_item(self.ui.cmb_settings.currentText())
        self.ui.cmb_settings.removeItem(self.ui.cmb_settings.currentIndex())
        self._current_settings[setting_name] = setting_value
        self._forbidden_settings.add(setting_name)
