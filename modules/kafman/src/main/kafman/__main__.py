#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@project: HsPyLib-Kafman
@package: kafman
   @file: __main__.py
@created: Fri, 1 Jul 2022
 @author: "<B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
   @site: "https://github.com/yorevs/hspylib")
@license: MIT - Please refer to <https://opensource.org/licenses/MIT>

Copyright·(c)·2024,·HSPyLib
"""

from hqt.qt_application import QtApplication
from hspylib.core.enums.charset import Charset
from hspylib.core.zoned_datetime import now
from hspylib.modules.application.version import Version
from kafman.__classpath__ import classpath
from kafman.views.main_qt_view import MainQtView
from textwrap import dedent

import logging as log
import sys


class Main(QtApplication):
    """Kafman application main class"""

    # The welcome message
    DESCRIPTION = classpath.get_source("welcome.txt").read_text(
        encoding=Charset.UTF_8.val
    )

    # Location of the .version file
    VERSION = Version.load(load_dir=classpath.source_path)

    # Location of the resources dir
    RESOURCE_DIR = str(classpath.resource_path)

    # Location of the UI font
    FONT_PATH = classpath.get_resource(
        "fonts/Droid-Sans-Mono-for-Powerline-Nerd-Font-Complete.otf"
    )

    # Application icon
    APP_ICON_PATH = classpath.get_resource("app-icon.png")

    def __init__(self, app_name: str):
        description = self.DESCRIPTION.format(self.VERSION)
        super().__init__(
            MainQtView,
            app_name,
            self.VERSION,
            description,
            resource_dir=self.RESOURCE_DIR,
        )
        self.set_application_font(self.FONT_PATH)
        self.set_application_icon(self.APP_ICON_PATH)
        log.info(dedent(f"""
        {self._app_name} v{self._app_version}

        Settings ==============================
                STARTED: {now("%Y-%m-%d %H:%M:%S")}
        """))


if __name__ == "__main__":
    # Application entry point
    Main("kafman").run(sys.argv[1:])
