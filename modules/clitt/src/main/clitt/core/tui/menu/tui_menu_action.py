#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
   @project: HsPyLib
   @package: clitt.core.tui.menu
      @file: tui_menu_action.py
   @created: Tue, 4 May 2021
    @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
      @site: https://github.com/yorevs/hspylib
   @license: MIT - Please refer to <https://opensource.org/licenses/MIT>

   Copyright·(c)·2024,·HSPyLib
"""
from clitt.core.tui.menu.tui_menu import OnTrigger_Cb, TUIMenu
from clitt.core.tui.menu.tui_menu_ui import TUIMenuUi
from typing import Optional


class TUIMenuAction(TUIMenu):
    """Represent a menu item action. Each action trigger a callback function."""

    def execute(self) -> Optional[TUIMenu]:
        self.render()
        if ret_menu := self._on_trigger(self._parent):
            return ret_menu
        return self._default_trigger_cb(self)

    def render(self) -> None:
        self.screen.cursor.restore()
        TUIMenuUi.render_app_title()

    def __init__(
        self,
        parent: TUIMenu,
        title: Optional[str] = None,
        tooltip: Optional[str] = None,
        on_trigger: OnTrigger_Cb = None,
    ):
        super().__init__(parent, title, tooltip)
        self._parent = parent
        self._on_trigger: OnTrigger_Cb = on_trigger or super()._default_trigger_cb

    def on_trigger(self, cb_on_trigger: OnTrigger_Cb) -> None:
        """Setter for the on_trigger callback. It is called when a menu item is triggered."""
        self._on_trigger = cb_on_trigger
