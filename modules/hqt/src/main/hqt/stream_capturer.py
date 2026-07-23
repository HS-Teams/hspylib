#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Hqt
@package: hqt
   @file: stream_capturer.py
@created: Wed, 30 Jun 2021
 @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: https://github.com/yorevs/hspylib
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from contextlib import redirect_stderr, redirect_stdout
from hspylib.core.preconditions import check_argument
from hspylib.core.tools.commons import is_debugging, syserr
from PyQt6.QtCore import pyqtSignal, QThread
from time import sleep

import io
import logging as log


class StreamCapturer(QThread):
    """QThread to captures stdout and/or stderr messages and send them via PyQt Signal"""

    stdoutCaptured = pyqtSignal(str)
    stderrCaptured = pyqtSignal(str)

    class StdoutWorker(QThread):
        """QThread worker to capture stdout messages"""

        streamCaptured = pyqtSignal(str)

        def __init__(self, parent: "StreamCapturer", poll_interval: float):
            super().__init__()
            self._poll_interval = poll_interval
            self._parent = parent

        def run(self):
            self.setObjectName(f"stdout-worker-{hash(self)}")
            with io.StringIO() as buf, redirect_stdout(buf):
                while (
                    not self._parent.isInterruptionRequested()
                    and not self.isInterruptionRequested()
                ):
                    output = buf.getvalue()
                    if output and output != "":
                        log.info(output)
                        self.streamCaptured.emit(output)
                        buf.seek(0)
                        buf.truncate(0)
                    sleep(self._poll_interval)

    class StderrWorker(QThread):
        """QThread worker to capture stderr messages"""

        streamCaptured = pyqtSignal(str)

        def __init__(self, parent: "StreamCapturer", poll_interval: float):
            super().__init__()
            self._poll_interval = poll_interval
            self._parent = parent

        def run(self):
            self.setObjectName("stderr-worker")
            with io.StringIO() as buf, redirect_stderr(buf):
                while (
                    not self._parent.isInterruptionRequested()
                    and not self.isInterruptionRequested()
                ):
                    output = buf.getvalue()
                    if output and output != "":
                        log.error(output)
                        self.streamCaptured.emit(output)
                        buf.seek(0)
                        buf.truncate(0)
                    sleep(self._poll_interval)

    def __init__(
        self,
        capture_stderr: bool = True,
        capture_stdout: bool = True,
        stdout_poll_interval: float = 0.5,
        stderr_poll_interval: float = 0.5,
    ):
        check_argument(
            capture_stderr or capture_stdout, "At least one capturer must be started"
        )
        super().__init__()
        self.setObjectName("stream-capturer")
        self._capture_stdout = capture_stdout
        self._capture_stderr = capture_stderr
        self._poll_interval = stdout_poll_interval + stderr_poll_interval

        if self._capture_stderr:
            self._stderr_capturer = self.StderrWorker(self, stderr_poll_interval)
            self._stderr_capturer.streamCaptured.connect(self.stderrCaptured.emit)
        if self._capture_stdout:
            self._stdout_capturer = self.StdoutWorker(self, stdout_poll_interval)
            self._stdout_capturer.streamCaptured.connect(self.stdoutCaptured.emit)

    def run(self) -> None:
        if self._capture_stderr:
            self._stderr_capturer.start()
        if self._capture_stdout:
            self._stdout_capturer.start()
        while not self.isInterruptionRequested():
            sleep(self._poll_interval)

    def start(
        self, priority: QThread.Priority = QThread.Priority.NormalPriority
    ) -> None:
        if not is_debugging():
            super().start(priority)
        else:
            syserr("Stderr/Stdout capture is not started in debugging mode")

    def quit(self) -> None:
        """Request interruption of the capturer and both child workers."""
        self.requestInterruption()
        if self._capture_stderr:
            self._stderr_capturer.requestInterruption()
        if self._capture_stdout:
            self._stdout_capturer.requestInterruption()
        super().quit()
