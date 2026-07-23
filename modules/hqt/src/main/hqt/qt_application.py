#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Hqt
@package: hqt
   @file: qt_application.py
@created: Wed, 30 Jun 2021
 @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: https://github.com/yorevs/hspylib
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from hspylib.core.preconditions import check_argument, check_state
from hspylib.core.tools.text_tools import titlecase
from hspylib.modules.application.application import Application
from hspylib.modules.application.exit_status import ExitStatus
from hspylib.modules.application.version import Version
from hqt.views.qt_view import QtView
from pathlib import Path
from PyQt6.QtGui import QFont, QFontDatabase, QIcon
from PyQt6.QtWidgets import QApplication
from typing import Optional, Type, TypeVar

import sys

V = TypeVar("V", bound=QtView)


class QtApplication(Application):
    def __init__(
        self,
        main_view: Type[V],
        name: str,
        version: Version,
        description: Optional[str] = None,
        usage: Optional[str] = None,
        epilog: Optional[str] = None,
        resource_dir: Optional[str] = None,
        log_dir: Optional[str] = None,
    ):
        super().__init__(
            name, version, description, usage, epilog, resource_dir, log_dir
        )
        app_title = titlecase(name)
        self.qapp = QApplication.instance() or QApplication(sys.argv)
        self.main_view = main_view()
        self.main_view.window.setWindowTitle(f"{app_title} v{str(version)}")
        self.qapp.setApplicationDisplayName(app_title)
        self.qapp.setApplicationName(name)
        self.qapp.setApplicationVersion(str(version))
        self.qapp.setQuitOnLastWindowClosed(True)

    def _main(self, *params, **kwargs) -> ExitStatus:
        """Execute the application's main statements"""
        self.main_view.show()
        return ExitStatus.of(self.qapp.exec())

    def _cleanup(self) -> None:
        QApplication.exit()

    def _setup_arguments(self) -> None:
        pass

    def set_application_font(self, font_path: Path) -> None:
        """TODO"""
        check_argument(font_path.exists(), f"Could not find font at: {str(font_path)}")
        font_id = QFontDatabase.addApplicationFont(str(font_path))
        families = QFontDatabase.applicationFontFamilies(font_id)
        check_state(families is not None and len(families) == 1)
        self.qapp.setFont(QFont(families[0], 14))

    def set_application_icon(self, icon_path: Path) -> None:
        """TODO"""
        check_argument(
            icon_path.exists(), f"Could not find icon file at: {str(icon_path)}"
        )
        self.qapp.setWindowIcon(QIcon(str(icon_path)))
