#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Kafman
@package: kafman.core.consumer
   @file: consumer_worker.py
@created: Wed, 30 Jun 2021
 @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: https://github.com/yorevs/hspylib
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from confluent_kafka import DeserializingConsumer, TopicPartition
from confluent_kafka.error import ConsumeError, ValueDeserializationError
from hspylib.core.tools.commons import syserr
from kafman.core.schema.kafka_schema import KafkaSchema
from PyQt6.QtCore import pyqtSignal, QThread
from typing import Any, Dict, List, Optional

import threading


class ConsumerWorker(QThread):
    """Confluent Kafka Consumer with Qt.
    Example at https://docs.confluent.io/platform/current/tutorials/examples/clients/docs/python.html
    For all kafka settings: https://github.com/edenhill/librdkafka/blob/master/CONFIGURATION.md
    Ref:. https://github.com/confluentinc/confluent-kafka-python/blob/master/examples/json_consumer.py
    """

    messageConsumed = pyqtSignal(str, int, int, str)
    messageFailed = pyqtSignal(str)

    def __init__(self, poll_interval: float = 0.5):
        super().__init__()
        self.setObjectName("kafka-consumer")
        self._started = False
        self._poll_interval = poll_interval
        self._consumer: Optional[DeserializingConsumer] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._schema: Optional[KafkaSchema] = None

    def start_consumer(self, settings: Dict[str, Any], schema: KafkaSchema) -> None:
        """Start the Kafka consumer agent.
        :param settings: TODO
        :param schema: TODO
        """
        if self._consumer is None:
            self._schema = schema
            self._consumer = DeserializingConsumer(settings)
            self._started = True

    def stop_consumer(self) -> None:
        """Stop the Kafka consumer agent"""
        if self._consumer is not None:
            self._started = False
            if self._worker_thread and self._worker_thread.is_alive():
                self._worker_thread.join(timeout=max(1.0, self._poll_interval * 3))
            elif self._consumer is not None:
                self._consumer.close()
                self._consumer = None
                self._schema = None
            self._schema = None

    def consume(self, topics: List[str]) -> None:
        """Start the consumer thread."""
        if self._started:
            worker_thread = threading.Thread(target=self._consume, args=(topics,))
            worker_thread.name = f"kafka-consumer-worker-{hash(self)}"
            worker_thread.daemon = True
            self._worker_thread = worker_thread
            worker_thread.start()

    def is_started(self) -> bool:
        """Whether the consumer is started or not."""
        return self._started

    def commit(self, topic: str, partition: int, offset: int) -> None:
        """Commit the next offset for one exact topic partition."""
        if self._consumer is not None:
            topic_partition = TopicPartition(topic, partition, offset + 1)
            self._consumer.commit(offsets=[topic_partition], asynchronous=False)

    def schema(self) -> Optional[KafkaSchema]:
        """TODO"""
        return self._schema

    def _consume(self, topics: List[str]) -> None:
        """Consume messages from the selected Kafka topics."""
        consumer = self._consumer
        if consumer is None:
            return
        try:
            consumer.subscribe(topics)
            while self._started:
                try:
                    message = consumer.poll(self._poll_interval)
                    if message is None:
                        continue
                    if message.error():
                        self.messageFailed.emit(str(message.error()))
                    else:
                        self.messageConsumed.emit(
                            message.topic(),
                            message.partition(),
                            message.offset(),
                            str(message.value()),
                        )
                except (ValueDeserializationError, ConsumeError) as err:
                    self.messageFailed.emit(str(err))
        except KeyboardInterrupt:
            syserr("Keyboard interrupted")
        finally:
            consumer.close()
            if self._consumer is consumer:
                self._consumer = None
            self._worker_thread = None
            self._schema = None
            self._started = False
