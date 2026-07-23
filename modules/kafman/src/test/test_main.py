#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Regression tests for Kafman's schema and runtime integration."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from types import MethodType, SimpleNamespace
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from confluent_kafka import TopicPartition
from hqt.qt_application import QtApplication
from hqt.promotions.hlistwidget import HListWidget
from hqt.promotions.hstacked_widget import HStackedWidget
from hspylib.core.exception.exceptions import InvalidInputError
from hspylib.core.zoned_datetime import now_ms
from kafman.__main__ import Main
from kafman.core.consumer.consumer_worker import ConsumerWorker
from kafman.core.producer.producer_worker import ProducerWorker
from kafman.core.schema.avro.avro_schema import AvroSchema
from kafman.core.schema.avro.field.fixed_field import FixedField
from kafman.core.schema.avro.field.map_field import MapField
from kafman.core.schema.avro.field.union_field import UnionField
from kafman.core.schema.json.json_schema import JsonSchema
from kafman.core.schema.schema_registry import SchemaRegistry
from kafman.core.statistics_worker import StatisticsWorker
from kafman.views.dialogs.settings_dialog import SettingsDialog
from kafman.views.main_qt_view import MainQtView
from kafman.views.promotions.form_area import FormArea
from PyQt6.QtGui import QFontInfo
from PyQt6.QtWidgets import QApplication, QWidget

SCHEMAS = Path(__file__).parents[1] / "main" / "kafman" / "resources" / "schemas"


class SchemaFormTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    @staticmethod
    def _form_payload(schema) -> dict:
        stack = HStackedWidget()
        schema.create_schema_form_widget(stack)
        area = FormArea(None)
        area.setWidget(stack)
        return json.loads(area.values())

    def test_all_bundled_avro_forms_build_and_validate(self) -> None:
        for filepath in sorted((SCHEMAS / "avro").glob("*.avsc")):
            with self.subTest(schema=filepath.name):
                schema = AvroSchema(str(filepath), "http://localhost:8081")
                payload = self._form_payload(schema)
                schema.validate(payload)

    def test_all_bundled_json_forms_build_and_validate(self) -> None:
        for filepath in sorted((SCHEMAS / "json").glob("*.json")):
            with self.subTest(schema=filepath.name):
                schema = JsonSchema(str(filepath), "http://localhost:8081")
                payload = self._form_payload(schema)
                schema.validate(payload)

    def test_avro_map_fixed_union_and_null_are_preserved(self) -> None:
        content = {
            "type": "record",
            "name": "ExtendedTypes",
            "fields": [
                {
                    "name": "labels",
                    "type": {"type": "map", "values": "long"},
                    "default": {},
                },
                {"name": "hash", "type": {"type": "fixed", "name": "Hash4", "size": 4}},
                {"name": "choice", "type": ["string", "int"]},
                {"name": "optional", "type": ["null", "string"], "default": None},
            ],
        }
        with tempfile.NamedTemporaryFile(
            "w", suffix=".avsc", encoding="utf-8"
        ) as schema_file:
            json.dump(content, schema_file)
            schema_file.flush()
            schema = AvroSchema(schema_file.name, "http://localhost:8081")
            fields = {field.name: field for field in schema.get_schema_fields()}
        self.assertIsInstance(fields["labels"], MapField)
        self.assertIsInstance(fields["hash"], FixedField)
        self.assertIsInstance(fields["choice"], UnionField)
        self.assertTrue(fields["optional"].nullable)

    def test_top_level_avro_array_is_supported(self) -> None:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".avsc", encoding="utf-8"
        ) as schema_file:
            json.dump({"type": "array", "items": "int"}, schema_file)
            schema_file.flush()
            schema = AvroSchema(schema_file.name, "http://localhost:8081")
            payload = self._form_payload(schema)
            schema.validate(payload)
        self.assertEqual({"value": []}, payload)

    def test_avro_union_and_binary_values_round_trip_with_native_types(self) -> None:
        content = {
            "type": "record",
            "name": "NativeTypes",
            "fields": [
                {"name": "choice", "type": ["string", "int"]},
                {"name": "payload", "type": "bytes"},
            ],
        }
        with tempfile.NamedTemporaryFile(
            "w", suffix=".avsc", encoding="utf-8"
        ) as schema_file:
            json.dump(content, schema_file)
            schema_file.flush()
            schema = AvroSchema(schema_file.name, "http://localhost:8081")
            native = schema.to_dict('{"choice": 7, "payload": "base64:AQI="}', None)
        self.assertEqual(7, native["choice"])
        self.assertEqual(b"\x01\x02", native["payload"])
        self.assertIn("base64:AQI=", schema.from_dict(native, None))

    def test_nested_avro_record_default_populates_child_fields(self) -> None:
        content = {
            "type": "record",
            "name": "Envelope",
            "fields": [
                {
                    "name": "nested",
                    "type": {
                        "type": "record",
                        "name": "Nested",
                        "fields": [{"name": "text", "type": "string"}],
                    },
                    "default": {"text": "seed"},
                }
            ],
        }
        with tempfile.NamedTemporaryFile(
            "w", suffix=".avsc", encoding="utf-8"
        ) as schema_file:
            json.dump(content, schema_file)
            schema_file.flush()
            schema = AvroSchema(schema_file.name, "http://localhost:8081")
            payload = self._form_payload(schema)
        self.assertEqual({"nested": {"text": "seed"}}, payload)

    def test_json_references_create_nested_forms(self) -> None:
        schema = JsonSchema(
            str(SCHEMAS / "json" / "card.json"), "http://localhost:8081"
        )
        stack = HStackedWidget()
        schema.create_schema_form_widget(stack)
        self.assertGreater(stack.count(), 1)

    def test_required_json_array_stays_an_array(self) -> None:
        schema = JsonSchema(
            str(SCHEMAS / "json" / "stock.json"), "http://localhost:8081"
        )
        payload = self._form_payload(schema)
        self.assertIsInstance(payload["market"], list)
        self.assertIsInstance(payload["state"], list)


class RuntimeRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_bundled_droid_font_loads_with_qt6(self) -> None:
        qt_app = object.__new__(QtApplication)
        qt_app.qapp = self.app
        original_font = self.app.font()
        try:
            font = qt_app.set_application_font(Main.FONT_PATH)
            font_info = QFontInfo(font)
            self.assertEqual("DroidSansMono Nerd Font", font_info.family())
            self.assertTrue(font_info.fixedPitch())
        finally:
            self.app.setFont(original_font)

    def test_settings_dialog_parses_embedded_properties(self) -> None:
        current = {}
        parent = QWidget()
        dialog = SettingsDialog(
            parent, SettingsDialog.SettingsType.PRODUCER, current, HListWidget(parent)
        )
        self.assertGreater(dialog.ui.cmb_settings.count(), 0)
        self.assertNotIn("key.serializer", current)

    def test_registry_registration_includes_schema_type(self) -> None:
        registry = SchemaRegistry("http://registry:8081")
        registry._valid = True
        captured = []

        def capture(self, url, **kwargs):
            captured.append((url, kwargs))
            return SimpleNamespace(body='{"id": 1}')

        registry._make_request = MethodType(capture, registry)
        registry.register("Order", '{"type":"object"}', "JSON")
        body = json.loads(captured[0][1]["body"])
        self.assertEqual("JSON", body["schemaType"])
        self.assertEqual('{"type":"object"}', body["schema"])

    def test_registry_multiple_versions_keep_subject_name_in_url(self) -> None:
        registry = SchemaRegistry("http://registry:8081")
        registry._valid = True
        registry._subjects = ["orders"]
        urls = []

        def respond(self, url, **kwargs):
            urls.append(url)
            if url.endswith("/versions"):
                return SimpleNamespace(body="[1, 2]")
            version = int(url.rsplit("/", 1)[-1])
            body = {
                "schemaType": "AVRO",
                "subject": "orders",
                "id": 1,
                "version": version,
                "schema": '{"type":"string"}',
            }
            return SimpleNamespace(body=json.dumps(body))

        registry._make_request = MethodType(respond, registry)
        subjects = registry.fetch_subject_versions()
        self.assertEqual(2, len(subjects))
        self.assertTrue(all("/subjects/orders/versions/" in url for url in urls[1:]))

    def test_consumer_commits_one_topic_partition(self) -> None:
        worker = ConsumerWorker()
        worker._consumer = MagicMock()
        worker.commit("orders", 3, 41)
        offsets = worker._consumer.commit.call_args.kwargs["offsets"]
        self.assertEqual(1, len(offsets))
        self.assertIsInstance(offsets[0], TopicPartition)
        self.assertEqual(
            ("orders", 3, 42),
            (offsets[0].topic, offsets[0].partition, offsets[0].offset),
        )

    def test_statistics_emit_values_before_reset(self) -> None:
        worker = StatisticsWorker()
        captured = []
        worker.statisticsReported.connect(lambda *values: captured.append(values))
        worker._started_ts = now_ms() - 1000
        worker.report_produced(3)
        worker.report_consumed(2)
        worker._tick()
        self.assertEqual((3, 2), captured[0][2:4])
        self.assertEqual((0, 0), worker.get_in_a_tick())

    def test_producer_flushes_once_per_batch(self) -> None:
        producer = MagicMock()
        schema = MagicMock()
        schema.key.return_value = "key"
        worker = ProducerWorker(flush_timeout=1)
        worker._producer = producer
        worker._schema = schema
        worker._started = True
        worker._produce(["orders"], ["one", "two"])
        self.assertEqual(2, producer.produce.call_count)
        producer.flush.assert_called_once_with(1)

    def test_invalid_form_blocks_message_creation(self) -> None:
        fake = SimpleNamespace(
            ui=SimpleNamespace(scr_schema_fields=SimpleNamespace(values=lambda: "{}")),
            _validate_schema_form=lambda: False,
        )
        with self.assertRaises(InvalidInputError):
            MainQtView._form_to_message(fake)


if __name__ == "__main__":
    unittest.main(verbosity=2)
