#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Kafman
@package: kafman.core.consumer
   @file: consumer_config.py
@created: Thu, 5 Aug 2021
 @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: https://github.com/yorevs/hspylib
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from abc import ABC
from typing import Any, Dict, List


class ConsumerConfig(ABC):
    """Some of the confluence exposed consumer properties."""

    # fmt: off
    BOOTSTRAP_SERVERS   = "bootstrap.servers"
    GROUP_ID            = "group.id"
    CLIENT_ID           = "client.id"
    ENABLE_AUTO_COMMIT  = "enable.auto.commit"
    SESSION_TIMEOUT_MS  = "session.timeout.ms"
    AUTO_OFFSET_RESET   = "auto.offset.reset"
    KEY_DESERIALIZER    = "key.deserializer"
    VALUE_DESERIALIZER  = "value.deserializer"
    # fmt: on

    @classmethod
    def required_settings(cls) -> List[str]:
        return [cls.BOOTSTRAP_SERVERS, cls.GROUP_ID, cls.CLIENT_ID]

    @classmethod
    def defaults(cls) -> Dict[str, Any]:
        return {
            "consumer": {
                cls.BOOTSTRAP_SERVERS: "localhost:9092",
                cls.GROUP_ID: "kafman_testing_group",
                cls.CLIENT_ID: "kafman_client_1",
                cls.ENABLE_AUTO_COMMIT: False,
                cls.SESSION_TIMEOUT_MS: 6000,
                cls.AUTO_OFFSET_RESET: "earliest",
            }
        }
