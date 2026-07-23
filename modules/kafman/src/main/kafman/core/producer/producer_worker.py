#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Kafman
@package: kafman.core.producer
   @file: producer_worker.py
@created: Wed, 30 Jun 2021
 @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: https://github.com/yorevs/hspylib
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from avro.errors import AvroTypeException
from confluent_kafka import SerializingProducer
from confluent_kafka.cimpl import KafkaError
from confluent_kafka.error import ValueSerializationError
from hspylib.core.tools.commons import syserr
from kafman.core.schema.kafka_schema import KafkaSchema
from PyQt6.QtCore import pyqtSignal, QThread
from typing import Any, List, Optional, Union

import threading


class ProducerWorker(QThread):
    """Confluent Kafka Producer with Qt.
    Example at: # Example at https://docs.confluent.io/platform/current/tutorials/examples/clients/docs/python.html
    For all kafka settings: https://github.com/edenhill/librdkafka/blob/master/CONFIGURATION.md
    Ref:. https://github.com/confluentinc/confluent-kafka-python/blob/master/examples/json_producer.py
    """

    messageProduced = pyqtSignal(str, int, int, str)
    messageFailed = pyqtSignal(str)

    def __init__(self, poll_interval: float = 0.5, flush_timeout: int = 30):
        super().__init__()
        self.setObjectName("kafka-producer")
        self._started = False
        self._poll_interval = poll_interval
        self._flush_timeout = flush_timeout
        self._producer: Optional[SerializingProducer] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._schema: Optional[KafkaSchema] = None

    def start_producer(self, settings: dict, schema: KafkaSchema) -> None:
        """Start the producer"""
        if self._producer is None:
            self._schema = schema
            self._producer = SerializingProducer(settings)
            self._started = True

    def stop_producer(self) -> None:
        """Stop the producer."""
        if self._producer is not None:
            self._started = False
            if self._worker_thread and self._worker_thread.is_alive():
                self._worker_thread.join(timeout=self._flush_timeout + 1)
            self._flush()
            self._producer = None
            self._worker_thread = None
            self._schema = None

    def schema(self) -> Optional[KafkaSchema]:
        """TODO"""
        return self._schema

    def produce(self, topics: List[Any], messages: Union[str, List[str]]) -> None:
        """Create a worker thread to produce the messages to the specified topics."""
        if self._started and self._producer is not None:
            if self._worker_thread and self._worker_thread.is_alive():
                self.messageFailed.emit("A produce operation is already in progress")
                return
            self._worker_thread = threading.Thread(
                target=self._produce, args=(topics, messages)
            )
            self._worker_thread.name = f"kafka-producer-worker-{hash(self)}"
            self._worker_thread.daemon = True
            self._worker_thread.start()

    def is_started(self) -> bool:
        """Whether the producer is started or not."""
        return self._started

    def _flush(self, timeout: Optional[int] = None) -> None:
        """Wait for all messages in the Producer queue to be delivered."""
        if self._producer:
            self._producer.flush(
                timeout=self._flush_timeout if timeout is None else timeout
            )

    def _produce(self, topics: List[str], messages: Union[str, List[str]]) -> None:
        """Produce message to topic."""
        producer = self._producer
        schema = self._schema
        if producer is None or schema is None:
            return
        message_list = messages if isinstance(messages, list) else [messages]
        try:
            for topic in topics:
                if not self._started:
                    break
                for msg in message_list:
                    if not self._started:
                        break
                    try:
                        if msg:
                            producer.produce(
                                topic=topic,
                                key=schema.key(),
                                value=msg,
                                on_delivery=self._cb_message_produced,
                            )
                        producer.poll(self._poll_interval)
                    except KeyboardInterrupt:
                        syserr("Keyboard interrupted")
                    except (
                        AvroTypeException,
                        ValueError,
                        ValueSerializationError,
                    ) as err:
                        error_message = (
                            f"Invalid input => {str(err)}\nDiscarding record: {msg}"
                        )
                        syserr(error_message)
                        self.messageFailed.emit(error_message)
        finally:
            producer.flush(self._flush_timeout)

    def _cb_message_produced(self, error: Optional[KafkaError], message: Any) -> None:
        """Delivery report handler called on successful or failed delivery of message"""
        if error is not None:
            self.messageFailed.emit(str(error))
        else:
            self.messageProduced.emit(
                message.topic(),
                message.partition(),
                message.offset(),
                str(message.value()),
            )
