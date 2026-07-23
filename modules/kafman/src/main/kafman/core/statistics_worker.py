#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Kafman
@package: kafman.core
   @file: statistics.py
@created: Wed, 30 Jun 2021
 @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: https://github.com/yorevs/hspylib
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from hspylib.core.zoned_datetime import now_ms
from PyQt6.QtCore import pyqtSignal, QThread
from dataclasses import dataclass
from typing import Tuple


@dataclass
class _Statistics:
    total: int = 0
    in_a_tick: int = 0


class StatisticsWorker(QThread):
    """Statistics worker for kafka consumer and producer"""

    statisticsReported = pyqtSignal(int, int, int, int, int, int)

    def __init__(self, report_interval: int = 1):
        super().__init__()
        self.setObjectName("kafka-statistics")
        self._started_ts = now_ms()
        self._consumed = _Statistics()
        self._produced = _Statistics()
        self._report_interval = report_interval

    def report_consumed(self, amount: int = 1) -> None:
        """Report a consumed message"""
        self._consumed.in_a_tick += amount
        self._consumed.total += amount

    def report_produced(self, amount: int = 1) -> None:
        """Report a produced message"""
        self._produced.in_a_tick += amount
        self._produced.total += amount

    def get_total(self) -> Tuple[int, int]:
        """Retrieve the totals produced/consumed so far"""
        return self._produced.total, self._consumed.total

    def get_in_a_tick(self) -> Tuple[int, int]:
        """Retrieve the amount produced/consumed in a tick"""
        return self._produced.in_a_tick, self._consumed.in_a_tick

    def run(self) -> None:
        while not self.isInterruptionRequested():
            self.sleep(self._report_interval)
            self._tick()

    def stop(self) -> None:
        """Request a clean worker shutdown and wait for it to finish."""
        self.requestInterruption()
        self.wait((self._report_interval + 1) * 1000)

    def _tick(self) -> None:
        """Tick and report current tick statistics, preparing for the next tick"""
        diff_time = max(1, int(now_ms() - self._started_ts))
        produced_in_a_tick = self._produced.in_a_tick
        consumed_in_a_tick = self._consumed.in_a_tick
        self.statisticsReported.emit(
            self._produced.total,
            self._consumed.total,
            produced_in_a_tick,
            consumed_in_a_tick,
            int(self._produced.total * 1000 / diff_time),
            int(self._consumed.total * 1000 / diff_time),
        )
        self._produced.in_a_tick = 0
        self._consumed.in_a_tick = 0
