#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Kafman
@package: kafman.views
   @file: main_qt_view.py
@created: Wed, 30 Jun 2021
 @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: https://github.com/yorevs/hspylib
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from clitt.core.icons.font_awesome.dashboard_icons import DashboardIcons
from clitt.core.icons.font_awesome.form_icons import FormIcons
from confluent_kafka.cimpl import Consumer
from copy import deepcopy
from hqt.promotions.hstacked_widget import HStackedWidget
from hqt.promotions.htablemodel import HTableModel
from hqt.stream_capturer import StreamCapturer
from hqt.views.qt_view import QtView
from hspylib.core.enums.charset import Charset
from hspylib.core.exception.exceptions import InvalidInputError, InvalidStateError
from hspylib.core.preconditions import check_state
from hspylib.core.tools.commons import dirname
from hspylib.core.tools.text_tools import (
    strip_escapes,
    strip_extra_spaces,
    strip_linebreaks,
)
from hspylib.core.zoned_datetime import now, now_ms
from hspylib.modules.fetch.fetch import is_reachable
from json.decoder import JSONDecodeError
from kafman.__classpath__ import classpath
from kafman.core.constants import MAX_HISTORY_SIZE_BYTES, StatusColor
from kafman.core.consumer.consumer_config import ConsumerConfig
from kafman.core.consumer.consumer_worker import ConsumerWorker
from kafman.core.exception.exceptions import InvalidSchemaError, SchemaRegistryError
from kafman.core.kafka_message import KafkaMessage
from kafman.core.producer.producer_config import ProducerConfig
from kafman.core.producer.producer_worker import ProducerWorker
from kafman.core.schema.avro.avro_schema import AvroSchema
from kafman.core.schema.json.json_schema import JsonSchema
from kafman.core.schema.kafka_schema import KafkaSchema
from kafman.core.schema.plain_schema import PlainSchema
from kafman.core.schema.registry_subject import RegistrySubject
from kafman.core.schema.schema_factory import SchemaFactory
from kafman.core.schema.schema_registry import SchemaRegistry
from kafman.core.schema.schema_type import SchemaType
from kafman.core.statistics_worker import StatisticsWorker
from kafman.views.dialogs.filters_dialog import FiltersDialog
from kafman.views.dialogs.settings_dialog import SettingsDialog
from kafman.views.indexes import StkProducerEdit, StkTools, Tabs
from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import ast
import atexit
import json
import logging as log
import os
import pprint
import re


class MainQtView(QtView):
    """Main application view"""

    VERSION = classpath.get_source(".version").read_text(encoding=Charset.UTF_8.val)

    SCHEMA_DIR = classpath.resource_path / "schemas"

    FORMS_DIR = str(classpath.resource_path / "forms")

    HISTORY_FILE = f"{os.getenv('HOME', os.getcwd())}/.kafman-history.properties"

    KAFKA_INTERNAL_TOPICS = (
        "_confluent",
        "_schemas",
        "__consumer_offsets",
        "__transaction_state",
    )

    @staticmethod
    def _supported_schemas() -> str:
        """Return a list of the supported serialization schema"""
        schemas = []
        schemas.extend(AvroSchema.extensions())
        schemas.extend(JsonSchema.extensions())
        return " ".join(schemas)

    @staticmethod
    def _is_json(text: str) -> bool:
        """Whether the provided text is a json code or not"""
        if not text:
            return False
        t = text.strip()
        return (t.startswith("{") and t.endswith("}")) or (
            t.startswith("[") and t.endswith("]")
        )

    def __init__(self):
        # Must come after the initialization above
        super().__init__(load_dir=self.FORMS_DIR)
        self._started = False
        self._registry = SchemaRegistry()
        self._consumer = ConsumerWorker()
        self._consumer.messageConsumed.connect(self._message_consumed)
        self._consumer.messageFailed.connect(self._display_error)
        self._producer = ProducerWorker()
        self._producer.messageProduced.connect(self._message_produced)
        self._producer.messageFailed.connect(self._display_error)
        self._all_settings: Dict[str, Dict[str, Any]] = {}
        self._all_settings.update(ProducerConfig.defaults())
        self._all_settings.update(ConsumerConfig.defaults())
        self._last_schema_dir = str(self.SCHEMA_DIR)
        self._last_used_dir = os.getcwd()
        self._all_schemas: Dict[str, KafkaSchema] = {}
        self._stats = StatisticsWorker()
        self._stats.statisticsReported.connect(self._update_stats)
        self._stats.start()
        self._capturer = StreamCapturer()
        self._capturer.stderrCaptured.connect(self._console_print_err)
        self._capturer.stdoutCaptured.connect(self._console_print)
        self._display_text(f"Application started at {now()}<br/>{'-' * 45}<br/>")
        self._setup_ui()
        self._load_history()
        list(map(self.ui.lst_cons_settings.set_item, self._all_settings["consumer"]))
        list(map(self.ui.lst_prod_settings.set_item, self._all_settings["producer"]))
        atexit.register(self._save_history)
        atexit.register(self._stop_workers)
        atexit.register(self._capturer.quit)
        self._capturer.start()

    def _setup_ui(self) -> None:
        """Setup UI: Connect signals and Setup components"""
        self.window.resize(1024, 768)
        self._setup_general_controls()
        self._setup_producer_controls()
        self._setup_consumer_controls()

    def _setup_general_controls(self):
        """Setup general components"""
        self.ui.splitter_pane.setSizes([350, 824])
        self.ui.tool_box.setCurrentIndex(StkTools.SETTINGS.value)
        self.ui.tab_widget.currentChanged.connect(self._activate_tab)
        self.ui.lbl_status_text.setTextFormat(Qt.TextFormat.RichText)
        self.ui.lbl_status_text.set_elidable(True)
        self.ui.lbl_status_text.set_dynamic_tooltip(True)
        self.ui.tbtn_test_registry_url.setText(FormIcons.CHECK_CIRCLE.value)
        self.ui.tbtn_test_registry_url.clicked.connect(
            lambda: self._test_registry_url(pop_warn_box=True)
        )
        self.ui.tbtn_sel_schema.setText(DashboardIcons.FOLDER_OPEN.value)
        self.ui.tbtn_sel_schema.clicked.connect(self._add_schema)
        self.ui.tbtn_desel_schema.setText(FormIcons.DESELECT.value)
        self.ui.tbtn_desel_schema.clicked.connect(self._deselect_schema)
        self.ui.tbtn_del_schema.setText(FormIcons.MINUS.value)
        self.ui.tbtn_del_schema.released.connect(self.ui.cmb_sel_schema.del_item)
        self.ui.cmb_registry_url.lineEdit().editingFinished.connect(
            self._invalidate_registry_url
        )
        self.ui.cmb_sel_schema.currentTextChanged.connect(self._change_schema)
        self.ui.cmb_registry_url.lineEdit().setPlaceholderText(
            "The registry server url"
        )
        self.ui.tbtn_registry_refresh.setText(FormIcons.REFRESH.value)
        self.ui.tbtn_registry_refresh.clicked.connect(self._refresh_registry_subjects)
        self.ui.tbl_registry.add_custom_menu_action(
            "Deregister subjects", self._deregister_subject, True
        )
        self.ui.txt_sel_schema.set_clearable(False)

    def _setup_producer_controls(self):
        """Setup producer components"""
        self.ui.cmb_prod_topics.lineEdit().setPlaceholderText(
            "Select or type a new kafka topic"
        )
        self.ui.tbtn_prod_settings_add.clicked.connect(self._add_producer_setting)
        self.ui.tbtn_prod_settings_add.setText(FormIcons.PLUS.value)
        self.ui.tbtn_prod_settings_del.clicked.connect(self._del_setting)
        self.ui.tbtn_prod_settings_del.setText(FormIcons.MINUS.value)
        self.ui.tbtn_prod_connect.clicked.connect(self._toggle_start_producer)
        self.ui.tbtn_prod_connect.setText(DashboardIcons.PLUG_IN.value)
        self.ui.tbtn_prod_connect.setStyleSheet("QToolButton {color: #2380FA;}")
        self.ui.tbtn_produce.clicked.connect(self._produce)
        self.ui.tbtn_produce.setText(DashboardIcons.SEND.value)
        self.ui.tbtn_prod_clear_topics.setText(FormIcons.CLEAR.value)
        self.ui.tbtn_prod_find_topics.setText(DashboardIcons.SEARCH.value)
        self.ui.tbtn_prod_find_topics.clicked.connect(
            lambda: self._fetch_broker_topics(is_producer=True)
        )
        self.ui.tbtn_prod_add_topics.setText(FormIcons.PLUS.value)
        self.ui.tbtn_prod_add_topics.clicked.connect(self._add_topic)
        self.ui.tbtn_prod_del_topics.setText(FormIcons.MINUS.value)
        self.ui.tbtn_prod_open_file.setText(DashboardIcons.FOLDER_OPEN.value)
        self.ui.tbtn_prod_open_file.clicked.connect(self._open_message_file)
        self.ui.tbtn_prod_save_file.setText(DashboardIcons.SAVE.value)
        self.ui.tbtn_prod_save_file.clicked.connect(self._save_message_file)
        self.ui.tbtn_prod_del_topics.clicked.connect(
            lambda: self._del_topic(is_producer=True)
        )
        self.ui.lst_prod_settings.currentRowChanged.connect(self._get_setting)
        self.ui.lst_prod_settings.set_editable()
        self.ui.lst_prod_settings.itemChanged.connect(self._edit_setting)
        self.ui.le_prod_settings.editingFinished.connect(self._edit_setting)
        self.ui.tbtn_format_msg.setText(DashboardIcons.FORMAT.value)
        self.ui.tbtn_format_msg.clicked.connect(self._format_message)
        self.ui.tbtn_form_view.setText(DashboardIcons.FORM.value)
        self.ui.tbtn_form_view.clicked.connect(
            lambda: self.ui.stk_producer_edit.slide_to_index(StkProducerEdit.FORM.value)
        )
        self.ui.tbtn_text_view.setText(DashboardIcons.CODE.value)
        self.ui.tbtn_text_view.clicked.connect(
            lambda: self.ui.stk_producer_edit.slide_to_index(StkProducerEdit.TEXT.value)
        )
        self.ui.tbtn_export_form.setText(DashboardIcons.EXPORT.value)
        self.ui.tbtn_export_form.clicked.connect(self._export_form)
        self.ui.tbtn_validate_form.setText(FormIcons.CHECK.value)
        self.ui.tbtn_validate_form.clicked.connect(self._validate_schema_form)
        self.ui.txt_producer.textChanged.connect(self._verify_message)
        self.ui.txt_producer.setReadOnly(False)
        self.ui.txt_producer.set_show_line_numbers(True)
        self.ui.txt_producer.set_highlight_enable(True)
        self.ui.tbtn_prod_clear_on_send_txt.setText(FormIcons.CLEAR.value)
        self.ui.tbtn_prod_clear_on_send_form.setText(FormIcons.CLEAR.value)
        self.ui.stk_producer_edit.currentChanged.connect(self._build_schema_layout)
        self.ui.stk_producer_edit.setCurrentIndex(StkProducerEdit.TEXT.value)

    def _setup_consumer_controls(self):
        """Setup consumer components"""
        self.ui.cmb_cons_topics.lineEdit().setPlaceholderText(
            "Select or type a new kafka topic"
        )
        self.ui.tbtn_cons_settings_add.clicked.connect(self._add_consumer_setting)
        self.ui.tbtn_cons_settings_add.setText(FormIcons.PLUS.value)
        self.ui.tbtn_cons_settings_del.clicked.connect(self._del_setting)
        self.ui.tbtn_cons_settings_del.setText(FormIcons.MINUS.value)
        self.ui.tbtn_cons_connect.clicked.connect(self._toggle_start_consumer)
        self.ui.tbtn_cons_connect.setText(DashboardIcons.PLUG_IN.value)
        self.ui.tbtn_cons_connect.setStyleSheet("QToolButton {color: #2380FA;}")
        self.ui.tbtn_cons_clear_topics.setText(FormIcons.CLEAR.value)
        self.ui.tbtn_cons_find_topics.setText(DashboardIcons.SEARCH.value)
        self.ui.tbtn_cons_find_topics.clicked.connect(
            lambda: self._fetch_broker_topics(is_producer=False)
        )
        self.ui.tbtn_cons_add_topics.setText(FormIcons.PLUS.value)
        self.ui.tbtn_cons_add_topics.clicked.connect(
            lambda: self._add_topic(is_producer=False)
        )
        self.ui.tbtn_cons_del_topics.setText(FormIcons.MINUS.value)
        self.ui.tbtn_cons_del_topics.clicked.connect(
            lambda: self._del_topic(is_producer=False)
        )
        self.ui.tbtn_cons_filters.setText(FormIcons.FILTER.value)
        self.ui.tbtn_cons_filters.clicked.connect(self._add_consumer_filters)
        self.ui.tbtn_cons_filters_refresh.setText(FormIcons.REFRESH.value)
        self.ui.tbtn_cons_filters_refresh.clicked.connect(self.ui.tbl_consumer.refresh)
        self.ui.lst_cons_settings.currentRowChanged.connect(self._get_setting)
        self.ui.lst_cons_settings.set_editable()
        self.ui.lst_cons_settings.itemChanged.connect(self._edit_setting)
        self.ui.le_cons_settings.editingFinished.connect(self._edit_setting)
        self.ui.tbl_consumer.add_custom_menu_action(
            "Commit offset", self._commit_offset, True
        )
        HTableModel(self.ui.tbl_consumer, KafkaMessage)
        self.ui.lbl_cons_filters.setText(str(self.ui.tbl_consumer.filters()))

    def _is_producer(self) -> bool:
        """Whether producer or consumer tab is selected"""
        return self.ui.tab_widget.currentIndex() == Tabs.PRODUCER.value

    def _kafka_type(self) -> str:
        """Whether kafka type is producer or consumer"""
        return "producer" if self._is_producer() else "consumer"

    def _required_settings(self) -> List[str]:
        """Return the required consumer/producer settings to start properly"""
        return (
            ProducerConfig if self._is_producer() else ConsumerConfig
        ).required_settings()

    def _topics(self, is_producer: bool) -> Optional[List[str]]:
        """Return the selected topic or a list containing all of them"""
        cmb_topics = self.ui.cmb_prod_topics if is_producer else self.ui.cmb_cons_topics
        topics = (
            [cmb_topics.itemText(i) for i in range(cmb_topics.count())]
            if not cmb_topics.currentText()
            else [cmb_topics.currentText()]
        )
        return topics if len(topics) > 0 else None

    def _settings(self) -> Dict[str, Any]:
        """Return the configured settings"""
        settings = self._all_settings[self._kafka_type()]
        check_state(all(s in settings for s in self._required_settings()))
        return settings

    def _schema(self) -> KafkaSchema:
        """Return the active serialization schema"""
        schema = (
            self._producer.schema() if self._is_producer() else self._consumer.schema()
        )
        if not schema:
            schema = self._selected_schema()
        return schema

    def _selected_schema(self):
        """Return the selected schema"""
        sel_schema = self.ui.cmb_sel_schema.currentText()
        return (
            self._all_schemas[sel_schema]
            if sel_schema in self._all_schemas
            else PlainSchema()
        )

    def _messages(self) -> Union[str, List[str]]:
        """Return the selected messages or build a json message from form"""
        schema = self._schema()
        if (
            isinstance(schema, PlainSchema)
            or self.ui.stk_producer_edit.currentIndex() == StkProducerEdit.TEXT.value
        ):
            text = self.ui.txt_producer.toPlainText()
            msgs = [text] if self._is_json(text) else text.split("\n")
            return list(map(strip_linebreaks, filter(None, msgs)))

        return strip_extra_spaces(strip_linebreaks(self._form_to_message()))

    def _add_consumer_setting(self) -> None:
        settings_dlg = SettingsDialog(
            self.ui.splitter_pane,
            SettingsDialog.SettingsType.CONSUMER,
            self._settings(),
            self.ui.lst_cons_settings,
        )
        settings_dlg.set_window_title("Add a consumer setting")
        settings_dlg.show()

    def _add_producer_setting(self) -> None:
        settings_dlg = SettingsDialog(
            self.ui.splitter_pane,
            SettingsDialog.SettingsType.PRODUCER,
            self._settings(),
            self.ui.lst_prod_settings,
        )
        settings_dlg.set_window_title("Add a producer setting")
        settings_dlg.show()

    def _add_consumer_filters(self) -> None:
        filters_dlg = FiltersDialog(
            self.ui.splitter_pane, self.ui.tbl_consumer.filters()
        )
        filters_dlg.filtersChanged.connect(
            lambda s: self.ui.lbl_cons_filters.setText(f"Filters: {s}")
        )
        filters_dlg.show()

    def _open_message_file(self) -> None:
        file_tuple = QFileDialog.getOpenFileNames(
            self.ui.tab_widget,
            "Open file",
            self._last_used_dir or ".",
            "Select a message file (*.txt *.json *.csv)",
        )
        if file_tuple and file_tuple[0]:
            self._last_used_dir = dirname(file_tuple[0][0]) or "."
            self.ui.txt_producer.set_plain_text(
                Path(file_tuple[0][0]).read_text(encoding=Charset.UTF_8.val)
            )

    def _save_message_file(self) -> None:
        file_tuple = QFileDialog.getSaveFileName(
            self.ui.tab_widget,
            "Save file",
            self._last_used_dir or ".",
            "Save file as (*.*)",
        )
        if file_tuple and file_tuple[0]:
            self._last_used_dir = dirname(file_tuple[0]) or "."
            with open(Path(file_tuple[0]), "w", encoding=Charset.UTF_8.val) as fd_file:
                fd_file.write(self.ui.txt_producer.toPlainText())

    def _form_to_message(self, validate: bool = True) -> str:
        """Return the message built from the schema form"""
        message = self.ui.scr_schema_fields.values()
        if validate and not self._validate_schema_form():
            raise InvalidInputError("Schema form is not valid")

        return message

    def _export_form(self) -> None:
        """Export the message from the schema form to the producer text editor"""
        self.ui.txt_producer.set_plain_text(self._form_to_message(validate=False))
        self._format_message()
        self.ui.stk_producer_edit.slide_to_index(StkProducerEdit.TEXT.value)

    def _format_message(self) -> None:
        """Validate and format the producer json text"""
        text = self.ui.txt_producer.toPlainText()
        text = text.replace("'", '"')
        if self._is_json(text):
            try:
                formatted = json.dumps(json.loads(text), indent=2)
                self.ui.txt_producer.set_plain_text(formatted)
                self.ui.tbtn_format_msg.setStyleSheet("QToolButton {color: #28C941;}")
                self._display_text("The provided json is valid", StatusColor.green)
            except JSONDecodeError as err:
                self._display_error(f"Failed to format json => {str(err)}")
                self.ui.tbtn_format_msg.setStyleSheet("QToolButton {color: #FF554D;}")

    def _verify_message(self) -> None:
        """Sanity test to check if the producer text is eligible for formatting"""
        enabled = self._is_json(self.ui.txt_producer.toPlainText())
        self.ui.tbtn_format_msg.setEnabled(enabled)
        self.ui.tbtn_format_msg.setStyleSheet("QToolButton {}")

    def _validate_schema_form(self) -> bool:
        """Validate current schema form against the loaded schema"""
        schema = self._schema()
        try:
            json_form = json.loads(self.ui.scr_schema_fields.values())
            schema.validate(json_form)
            self._display_text("Schema form is valid", StatusColor.green)
            return True
        except Exception as err:  # pylint: disable=broad-except
            self._display_error(f"Schema form is not valid:: {err}")
            return False

    def _activate_tab(self, index: Optional[int] = None) -> None:
        """Set the selected tab"""
        index = index if index is not None else self.ui.tab_widget.currentIndex()
        self.ui.tab_widget.setCurrentIndex(index)
        self.ui.stk_settings.setCurrentIndex(index)
        self.ui.stk_statistics.setCurrentIndex(index)

    def _add_schema(self, file_tuple: Optional[Tuple[List[str], str]] = None) -> bool:
        """Select an serialization schema from the file picker dialog or from specified file"""
        ret_val = False
        if not file_tuple:
            file_tuple = QFileDialog.getOpenFileNames(
                self.ui.splitter_pane,
                "Open schema",
                self._last_schema_dir or ".",
                f"Schema files ({self._supported_schemas()})",
            )
        if file_tuple and len(file_tuple[0]):
            for schema_file in file_tuple[0]:
                self._last_schema_dir = dirname(schema_file) or "."
                registry_url = self._test_registry_url()
                if registry_url:
                    try:
                        schema = SchemaFactory.create_schema(schema_file, registry_url)
                        self._registry.register(
                            schema.get_schema_name(),
                            schema.get_content_text(),
                            schema.get_schema_type(),
                        )
                        self._all_schemas[schema.get_schema_name()] = schema
                        self.ui.cmb_sel_schema.set_item(schema.get_schema_name())
                        self.ui.cmb_registry_schema.set_item(schema.get_schema_name())
                        self.ui.cmb_sel_schema.setCurrentText(schema.get_schema_name())
                        self._display_text(f'Schema added: "{str(schema)}"')
                        ret_val = True
                    except InvalidSchemaError as err:
                        self._display_error(f"Unsupported schema: => {str(err)}")
                    except InvalidStateError as err:
                        self._display_error(f"Unable to add schema: => {str(err)}")
                    except SchemaRegistryError as err:
                        self._display_error(f"Unable to register schema: => {str(err)}")
        return ret_val

    def _deselect_schema(self):
        """Deselect current selected serialization schema"""
        self.ui.cmb_sel_schema.setCurrentIndex(-1)
        self.ui.stk_producer_edit.setCurrentIndex(StkProducerEdit.TEXT.value)

    def _change_schema(self, schema_name: str) -> None:
        """Change the current serialization schema text content"""
        if schema_name:
            content = self._all_schemas[schema_name].get_content_dict()
            self.ui.tool_box.setCurrentIndex(StkTools.SCHEMAS.value)
            self.ui.txt_sel_schema.set_plain_text(json.dumps(content, indent=1))
        else:
            self.ui.stk_producer_edit.setCurrentIndex(StkProducerEdit.TEXT.value)
            self.ui.txt_sel_schema.set_plain_text("")
            self.ui.cmb_sel_schema.setCurrentIndex(-1)
            self.ui.lbl_schema_fields.setText("Schema Fields")

    def _build_schema_layout(self) -> bool:
        """Build a form based on the selected schema using a grid layout"""
        schema = self._producer.schema() or self._selected_schema()
        if schema and schema.get_schema_type() != SchemaType.PLAIN.value:
            try:
                self._cleanup_schema_layout()
                form_widget = HStackedWidget(self.ui.tab_widget)
                form_widget.currentChanged.connect(self._schema_form_changed)
                form_widget.installEventFilter(form_widget)
                schema.create_schema_form_widget(form_widget)
                self.ui.scr_schema_fields.setWidget(form_widget)
                self._schema_form_changed(0)
                self.ui.lbl_schema_fields.setText(
                    f"{schema.get_schema_name()} Schema Fields"
                )
                return True
            except AttributeError as err:
                self.ui.cmb_sel_schema.removeItem(self.ui.cmb_sel_schema.currentIndex())
                self._display_error(f"Invalid schema {schema} was not loaded => {err}")
                raise InvalidStateError(err) from err
        return False

    def _cleanup_schema_layout(self) -> None:
        """Remove all widgets from the current grid layout"""
        layout = self.ui.scr_schema_fields.widget().layout()
        while layout and layout.count() > 0:
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _schema_form_changed(self, index: int):
        """Adjustments after schema form changed"""
        if index >= 0:
            form_stack = self.ui.scr_schema_fields.widget()
            if form_stack is not None and isinstance(form_stack, HStackedWidget):
                form_pane = form_stack.widget(index)
                if form_pane is not None:
                    obj_name = form_pane.objectName() or str(index)
                    form_name = f"{obj_name} Form"
                    self.ui.lbl_current_form.setText(form_name)

    def _get_setting(self) -> None:
        """Get a setting and display it on the proper line edit field"""
        lst = (
            self.ui.lst_prod_settings
            if self._is_producer()
            else self.ui.lst_cons_settings
        )
        edt = (
            self.ui.le_prod_settings
            if self._is_producer()
            else self.ui.le_cons_settings
        )
        ktype = self._kafka_type()
        item = lst.currentItem()
        if item and item.text():
            setting = item.text()
            if setting in self._all_settings[ktype]:
                edt.setText(str(self._all_settings[ktype][setting]))
            else:
                edt.setText("")
                self._all_settings[ktype][setting] = ""

    def _edit_setting(self) -> None:
        """Edit a setting from the proper line edit field"""
        lst = (
            self.ui.lst_prod_settings
            if self._is_producer()
            else self.ui.lst_cons_settings
        )
        edt = (
            self.ui.le_prod_settings
            if self._is_producer()
            else self.ui.le_cons_settings
        )
        ktype = self._kafka_type()
        item = lst.currentItem()
        if item:
            setting = item.text()
            old_setting = next(
                (
                    s
                    for i, s in enumerate(self._all_settings[ktype])
                    if i == lst.currentRow()
                ),
                "",
            )
            if setting:
                if setting not in self._all_settings[ktype]:
                    del self._all_settings[ktype][old_setting]
                if edt.text():
                    self._all_settings[ktype][setting] = edt.text()
                    self._display_text(
                        f"{ktype.capitalize()} setting '{setting}' saved"
                    )
                else:
                    self._all_settings[ktype][setting] = ""
            else:
                setting = old_setting
                edt.setText(self._all_settings[ktype][setting])
                item.setText(setting)
                if setting:
                    self._display_error(f"Setting {setting} is required")

    def _del_setting(self) -> None:
        """Delete a setting specified by the proper line edit field"""
        lst = (
            self.ui.lst_prod_settings
            if self._is_producer()
            else self.ui.lst_cons_settings
        )
        ktype = self._kafka_type()
        item = lst.currentItem()
        if item:
            setting = item.text()
            if setting and setting not in self._required_settings():
                lst.del_item(lst.currentRow())
                del self._all_settings[ktype][setting]
            else:
                self._display_error(f"Setting {setting} is required")

    def _fetch_broker_topics(self, is_producer: bool) -> None:
        """Find all topics from broker"""
        config = {
            k: v
            for (k, v) in self._all_settings["consumer"].items()
            if k in [ConsumerConfig.BOOTSTRAP_SERVERS, ConsumerConfig.GROUP_ID]
        }
        brokers = config[ConsumerConfig.BOOTSTRAP_SERVERS]
        if not is_reachable(brokers):
            self._display_error(
                f"Unable to connect to kafka brokers: [{brokers}]", pop_warn_box=True
            )
            return
        consumer = Consumer(config)
        topics = [
            k
            for (k, v) in consumer.list_topics().topics.items()
            if not k.startswith(self.KAFKA_INTERNAL_TOPICS)
            and not k.startswith(f"{config[ConsumerConfig.GROUP_ID]}--")
        ]
        self._display_text(f"Retrieved {len(topics)} topics from broker: {brokers}")
        consumer.close()
        for topic in topics:
            self._add_topic(topic, is_producer)

    def _add_topic(self, topic: Optional[str] = None, is_producer: bool = True) -> None:
        """Add a topic to the combo box."""
        if is_producer:
            new_topic = self.ui.cmb_prod_topics.currentText()
            cmb = self.ui.cmb_prod_topics
        else:
            new_topic = self.ui.cmb_cons_topics.currentText()
            cmb = self.ui.cmb_cons_topics
        if topic or new_topic:
            cmb.set_item(topic or new_topic)
            cmb.setEditText("")
        if cmb.count() >= 1:
            cmb.setCurrentIndex(0)

    def _del_topic(self, is_producer: bool) -> None:
        """Delete a topic to the combo box."""
        if not is_producer:
            del_topic = self.ui.cmb_cons_topics.currentText()
            cmb = self.ui.cmb_cons_topics
        else:
            del_topic = self.ui.cmb_prod_topics.currentText()
            cmb = self.ui.cmb_prod_topics
        if del_topic:
            self._display_text(
                f"Topic {del_topic} has been removed from {self._kafka_type()}"
            )
            cmb.removeItem(cmb.currentIndex())

    def _invalidate_registry_url(self) -> None:
        """Mark current schema registry url as not valid"""
        self.ui.tbtn_test_registry_url.setStyleSheet("")
        self.ui.tbtn_test_registry_url.setText(FormIcons.CHECK_CIRCLE.value)
        self._registry.invalidate()

    def _test_registry_url(
        self, skip_if_tested: bool = True, pop_warn_box: bool = False
    ) -> Optional[str]:
        """Check is the provided schema registry url is valid or not"""
        url = self.ui.cmb_registry_url.currentText()
        if self._registry.is_valid() and skip_if_tested:
            return url
        if url:
            if self._registry.set_url(url):
                self.ui.tbtn_test_registry_url.setText(FormIcons.CHECK_CIRCLE.value)
                self.ui.tbtn_test_registry_url.setStyleSheet(
                    "QToolButton {color: #28C941;}"
                )
                self._display_text(f"Host {url} succeeded", StatusColor.green)
            else:
                self.ui.tbtn_test_registry_url.setText(FormIcons.ERROR_CIRCLE.value)
                self.ui.tbtn_test_registry_url.setStyleSheet(
                    "QToolButton {color: #FF554D;}"
                )
                self._display_error(
                    f"Unable to connect to registry server: [{url}]",
                    pop_warn_box=pop_warn_box,
                )
        else:
            self.ui.tbtn_test_registry_url.setText(FormIcons.UNCHECK_CIRCLE.value)
            self.ui.tbtn_test_registry_url.setStyleSheet(
                "QToolButton {color: #FF554D;}"
            )

        return url

    def _commit_offset(self) -> None:
        """Commit the selected message offset for its exact topic partition."""
        table = self.ui.tbl_consumer
        model = table.model()
        sel_model = table.selectionModel()
        if model and sel_model and (indexes := sel_model.selectedIndexes()):
            message = model.row(indexes[0])
            self._consumer.commit(message.topic, message.partition, message.offset)
            self._display_text(
                f"Offset committed: {message.topic}[{message.partition}]@{message.offset}",
                StatusColor.yellow,
            )

    def _toggle_start_producer(self) -> None:
        """Start/Stop the producer."""
        started = self._producer.is_started()
        if started:  # Stop
            self.ui.tool_box.setCurrentIndex(StkTools.SETTINGS.value)
            self._producer.stop_producer()
            self._display_text("Production to kafka topics stopped", StatusColor.yellow)
            self.ui.stk_producer_edit.setCurrentIndex(StkProducerEdit.TEXT.value)
        else:  # Start
            topics = self._topics(True)
            if not topics:
                self._display_error(
                    "Must subscribe to at least one topic", pop_warn_box=True
                )
                return
            schema = self._schema()
            settings = deepcopy(self._settings())
            settings.update(schema.settings())
            settings = {
                k: v for k, v in settings.items() if not k.endswith(".deserializer")
            }
            schema_name = (
                f' using schema "{str(self._schema())}"' if self._schema() else ""
            )
            self.ui.tool_box.setCurrentIndex(StkTools.STATISTICS.value)
            self._producer.start_producer(settings, schema)
            self._display_text(
                f"Producer settings: {pprint.pformat(settings, indent=2)}"
            )
            self._display_text(
                f"Started producer. Topics: {topics}  Schema: {schema_name}",
                StatusColor.green,
            )

        self.ui.scr_schema_fields.setEnabled(not started)
        self.ui.cmb_prod_topics.setEnabled(started)
        self.ui.txt_producer.setEnabled(not started)
        self.ui.tbtn_format_msg.setEnabled(not started)
        self.ui.tbtn_export_form.setEnabled(not started)
        self.ui.tbtn_validate_form.setEnabled(not started)
        self.ui.tbtn_produce.setEnabled(not started)
        self.ui.tbtn_prod_open_file.setEnabled(not started)
        self.ui.tbtn_prod_save_file.setEnabled(not started)
        self.ui.tbtn_text_view.setEnabled(not started)
        self.ui.tbtn_form_view.setEnabled(not started)
        self.ui.tbtn_prod_add_topics.setEnabled(started)
        self.ui.tbtn_prod_del_topics.setEnabled(started)
        self.ui.tbtn_prod_clear_topics.setEnabled(started)
        self.ui.tbtn_prod_connect.setText(
            DashboardIcons.PLUG_IN.value if started else DashboardIcons.PLUG_OUT.value
        )
        self.ui.tbtn_prod_connect.setStyleSheet(
            "QToolButton {color: " + ("#FF554D" if not started else "#2380FA") + ";}"
        )

    def _toggle_start_consumer(self) -> None:
        """Start/Stop the consumer."""
        started = self._consumer.is_started()
        if started:  # Stop
            self.ui.tool_box.setCurrentIndex(StkTools.SETTINGS.value)
            self._consumer.stop_consumer()
            self._display_text(
                "Consumption from kafka topics stopped", StatusColor.yellow
            )
        else:  # Start
            topics = self._topics(False)
            if not topics:
                self._display_error(
                    "Must subscribe to at least one topic", pop_warn_box=True
                )
                return
            schema = self._schema()
            settings = deepcopy(self._settings())
            settings.update(schema.settings())
            settings = {
                k: v for k, v in settings.items() if not k.endswith(".serializer")
            }
            schema_name = (
                f' using schema "{str(self._schema())}"' if self._schema() else ""
            )
            self.ui.tool_box.setCurrentIndex(StkTools.STATISTICS.value)
            self._consumer.start_consumer(settings, schema)
            self._consumer.consume(topics)
            self._display_text(
                f"Consumer settings: {pprint.pformat(settings, indent=2)}"
            )
            self._display_text(
                f"Started consumer. Topics {topics}  Schema: {schema_name}",
                StatusColor.green,
            )

        self.ui.cmb_cons_topics.setEnabled(started)
        self.ui.tbtn_cons_add_topics.setEnabled(started)
        self.ui.tbtn_cons_del_topics.setEnabled(started)
        self.ui.tbtn_cons_clear_topics.setEnabled(started)
        self.ui.tbtn_cons_connect.setText("O" if started else "-")
        self.ui.tbtn_cons_connect.setText(
            DashboardIcons.PLUG_IN.value if started else DashboardIcons.PLUG_OUT.value
        )
        self.ui.tbtn_cons_connect.setStyleSheet(
            "QToolButton {color: " + ("#FF554D" if not started else "#2380FA") + ";}"
        )

    def _produce(self) -> None:
        """Produce messages to selected kafka topics"""
        try:
            messages = self._messages()
            if self._producer.is_started() and messages:
                topics = self._topics(True)
                if topics:
                    self._producer.produce(topics, messages)
        except InvalidInputError as err:
            self._display_error(str(err))

    def _display_error(
        self, message: str, console_print: bool = True, pop_warn_box: bool = False
    ) -> None:
        """Display an error at the status bar (and console if required)"""

        self._display_text(message, StatusColor.red, console_print, log_it=False)
        log.error(message)
        if pop_warn_box:
            QMessageBox.warning(
                self.ui.tab_widget,
                "Attention",
                message,
                QMessageBox.StandardButton.Ok,
            )

    def _display_text(
        self,
        message: str,
        color: Optional[QColor] = None,
        console_print: bool = True,
        log_it: bool = True,
    ) -> None:
        """Display a text at the status bar (and console if required)"""

        message = f"<font color='{color.name() if color else 'white'}'>{message}</font>"
        message = message.replace("\n", "<br/>")
        self.ui.lbl_status_text.setText(message)
        if console_print:
            self._console_print(f"-> {message}", color)
        if log_it:
            log.info(message)

    def _update_stats(
        self,
        produced_total: int,
        consumed_total: int,
        produced_in_a_tick: int,
        consumed_in_a_tick: int,
        average_produced: int,
        average_consumed: int,
    ) -> None:
        """Update the consumer and producer statistics"""

        self.ui.lbl_stats_produced.setText(str(produced_total))
        self.ui.lbl_stats_produced_ps.setText(str(produced_in_a_tick))
        self.ui.lbl_stats_produced_avg.setText(str(average_produced))
        self.ui.lbl_stats_consumed.setText(str(consumed_total))
        self.ui.lbl_stats_consumed_ps.setText(str(consumed_in_a_tick))
        self.ui.lbl_stats_consumed_avg.setText(str(average_consumed))

    def _message_produced(
        self, topic: str, partition: int, offset: int, value: str
    ) -> None:
        """Callback when a kafka message has been produced."""
        row = KafkaMessage(now_ms(), topic, partition, offset, value)
        text = f"-> Produced {row}"
        self._console_print(text, StatusColor.blue)
        self._stats.report_produced()
        self._display_text(
            f"Produced {self._stats.get_in_a_tick()[0]} messages to Kafka",
            StatusColor.blue,
            False,
        )
        clear_txt = self.ui.tbtn_prod_clear_on_send_txt.isChecked()
        if clear_txt:
            self.ui.txt_producer.clear()
        clear_form = self.ui.tbtn_prod_clear_on_send_form.isChecked()
        if clear_form:
            self._build_schema_layout()

    def _message_consumed(
        self, topic: str, partition: int, offset: int, value: str
    ) -> None:
        """Callback when a kafka message has been consumed."""
        row = KafkaMessage(now_ms(), topic, partition, offset, value)
        text = f"-> Consumed {row}"
        self.ui.tbl_consumer.model().push_data([row])
        self._console_print(text, StatusColor.orange)
        self._stats.report_consumed()

    def _refresh_registry_subjects(self) -> None:
        """Refresh all schema registry server subjects"""
        if self._registry.is_valid():
            if not self.ui.tbl_registry.model():
                HTableModel(self.ui.tbl_registry, RegistrySubject)
            else:
                self.ui.tbl_registry.model().clear()
            schema_types, subjects = self._registry.fetch_server_info()
            self._display_text(
                f"[Registry] Supported schema types: {schema_types}", StatusColor.purple
            )
            self._display_text(
                f"[Registry] Existing subjects: {subjects}", StatusColor.purple
            )
            versions = self._registry.fetch_subject_versions()
            self.ui.tbl_registry.model().push_data(versions)

    def _deregister_subject(self):
        """Deregister the schema from the registry server"""
        model = self.ui.tbl_registry.model()
        if model:
            indexes, subjects = self.ui.tbl_registry.model().selected_data()
            if subjects:
                self._registry.deregister(subjects)
                model.remove_rows(indexes)
                self._display_text(
                    f"Schema subjects [{', '.join([s.subject for s in subjects])}] successfully deregistered"
                )

    def _console_print(self, text: str, color: Optional[QColor] = None) -> None:
        """Append a message to the console."""
        if isinstance(text, str):
            msg = text
        else:
            raise TypeError("Expecting string or Event objects")
        self.ui.txt_console.push_text(strip_escapes(msg), color)

    def _console_print_err(self, text: str) -> None:
        """Append an error message to the console."""
        self._console_print(f"-> {text}", StatusColor.red)

    def _save_history(self):
        """Save current app history."""
        with open(self.HISTORY_FILE, "w", encoding="utf-8") as fd_history:
            prod_topics = [
                self.ui.cmb_prod_topics.itemText(i)
                for i in range(self.ui.cmb_prod_topics.count())
            ]
            cons_topics = [
                self.ui.cmb_cons_topics.itemText(i)
                for i in range(self.ui.cmb_cons_topics.count())
            ]
            schemas = [
                self._all_schemas[self.ui.cmb_sel_schema.itemText(i)].get_filepath()
                for i in range(self.ui.cmb_sel_schema.count())
            ]
            w_size = self.window.width(), self.window.height()
            s_size = self.ui.splitter_pane.sizes()[0], self.ui.splitter_pane.sizes()[1]
            fd_history.write(f"splitter_sizes = {str(s_size)}\n")
            fd_history.write(f"window_size = {str(w_size)}\n")
            fd_history.write(f"prod_topics = {prod_topics}\n")
            fd_history.write(f"cons_topics = {cons_topics}\n")
            fd_history.write(f"settings = {str(self._all_settings)}\n")
            fd_history.write(f"selected_tab = {self.ui.tab_widget.currentIndex()}\n")
            fd_history.write(f"last_used_dir = {self._last_used_dir}\n")
            fd_history.write(f"last_schema_dir = {self._last_schema_dir}\n")
            fd_history.write(f"schema = {schemas}\n")
            fd_history.write(f"last_schema = {self.ui.cmb_sel_schema.currentText()}\n")
            fd_history.write(
                f"registry_url = {self.ui.cmb_registry_url.currentText()}\n"
            )

    def _load_history(self):  # pylint: disable=too-many-branches
        """Load a previously saved app history."""
        if (
            os.path.exists(self.HISTORY_FILE)
            and os.stat(self.HISTORY_FILE).st_size <= MAX_HISTORY_SIZE_BYTES
        ):
            self._display_text("History recovered")
            with open(self.HISTORY_FILE, "r", encoding="utf-8") as fd_history:
                lines = fd_history.readlines()
                try:
                    for line in lines:
                        mat = re.search(r"(.*) ?= ?(.*)", line)
                        if mat:
                            prop_name = mat.group(1).strip()
                            prop_value = mat.group(2).strip()
                            if prop_name == "prod_topics":
                                list(map(self._add_topic, ast.literal_eval(prop_value)))
                            elif prop_name == "cons_topics":
                                list(
                                    map(
                                        lambda p: self._add_topic(p, False),
                                        ast.literal_eval(prop_value),
                                    )
                                )
                            elif prop_name == "settings":
                                settings = ast.literal_eval(prop_value)
                                if isinstance(settings, dict):
                                    self._all_settings = cast(
                                        Dict[str, Dict[str, Any]], settings
                                    )
                            elif prop_name == "window_size":
                                size = ast.literal_eval(prop_value)
                                self.window.resize(int(size[0]), int(size[1]))
                            elif prop_name == "splitter_sizes":
                                size = ast.literal_eval(prop_value)
                                self.ui.splitter_pane.setSizes(
                                    [int(size[0]), int(size[1])]
                                )
                            elif prop_name == "selected_tab":
                                self._activate_tab(
                                    int(prop_value or Tabs.PRODUCER.value)
                                )
                            elif prop_name == "last_schema_dir":
                                self._last_schema_dir = str(prop_value)
                            elif prop_name == "last_used_dir":
                                self._last_used_dir = prop_value
                            elif prop_name == "schema":
                                t_schema = (
                                    ast.literal_eval(prop_value),
                                    f"Schema files ({self._supported_schemas()})",
                                )
                                if len(t_schema[0]) > 0:
                                    self._add_schema(t_schema)
                            elif prop_name == "last_schema":
                                self.ui.cmb_sel_schema.setCurrentText(prop_value)
                            elif prop_name == "registry_url":
                                self.ui.cmb_registry_url.setCurrentText(
                                    prop_value or "localhost:8081"
                                )
                except ValueError:
                    log.warning(
                        'Invalid history value "%s" for setting "%s"',
                        prop_value,
                        prop_name,
                    )
        else:
            # Defaults
            self._display_text("Kafman history was not loaded")
            self._all_settings.update(ProducerConfig.defaults())
            self._all_settings.update(ConsumerConfig.defaults())
            self._activate_tab()

    def _stop_workers(self) -> None:
        """Stop background workers before the application exits."""
        self._producer.stop_producer()
        self._consumer.stop_consumer()
        self._stats.stop()
