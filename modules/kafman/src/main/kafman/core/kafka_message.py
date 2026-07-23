#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Kafman
@package: kafman.core
   @file: kafka_message.py
@created: Wed, 30 Jun 2021
 @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: https://github.com/yorevs/hspylib
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from typing import Optional


class KafkaMessage:
    """Represent a produced or consumed Kafka message"""

    def __init__(
        self,
        timestamp: Optional[int] = None,
        topic: Optional[str] = None,
        partition: Optional[int] = None,
        offset: Optional[int] = None,
        value: Optional[str] = None,
    ):
        self.timestamp = timestamp
        self.topic = topic
        self.partition = partition
        self.offset = offset
        self.value = value

    def __str__(self):
        return f"{self.timestamp} topic={self.topic} partition={self.partition} offset={self.offset} value={self.value}"

    def __repr__(self):
        return str(self)
