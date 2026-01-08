#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
   @project: HsPyLib
   @package: clitt.core.tui.menu
      @file: tui_menu_ui.py
   @created: Tue, 4 May 2021
    @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
      @site: https://github.com/yorevs/hspylib
   @license: MIT - Please refer to <https://opensource.org/licenses/MIT>

   Copyright·(c)·2024,·HSPyLib
"""
from clitt.core.term.terminal import Terminal
from clitt.core.tui.menu.tui_menu import TUIMenu
from clitt.core.tui.tui_preferences import TUIPreferences
from hspylib.core.metaclass.singleton import Singleton
from hspylib.core.preconditions import check_not_none


class TUIMenuUi(metaclass=Singleton):
    """Provide a menu for terminal UIs. Each sub-item must belong to the TUIMenu class and can be an instance of
    TUIMenuItem, TUIMenuAction or TUIMenuView.
    """

    INSTANCE: 'TUIMenuUi'

    APP_TITLE = "Main Menu"

    # fmt: off
    PREFS = TUIPreferences.INSTANCE

    SCREEN = Terminal.INSTANCE.screen

    MENU_LINE = f"{'--' * PREFS.title_line_length}"

    MENU_TITLE_FMT = (
        f"{PREFS.title_color}"
        f"+{MENU_LINE}+%EOL%"
        "|{title:^" + str(2 * PREFS.title_line_length) + "s}|%EOL%"
        f"+{MENU_LINE}+%EOL%%NC%"
    )
    # fmt: on

    @classmethod
    def render_app_title(cls, app_title: str = None) -> None:
        """Render the application title."""
        cls.SCREEN.clear()
        cls.SCREEN.cursor.writeln(cls.MENU_TITLE_FMT.format(title=app_title or cls.APP_TITLE))

    @staticmethod
    def back(source: TUIMenu) -> TUIMenu:
        """Return the parent menu from the source of the event.
        :param source: the source menu of the event.
        """
        return source.parent

    @staticmethod
    def quit(_) -> None:
        """Break the menu flow by returning None."""
        TUIMenuUi.INSTANCE._done = True

    def __init__(self, main_menu: TUIMenu, title: str = "Main Menu"):
        check_not_none(main_menu)
        super().__init__()
        TUIMenuUi.APP_TITLE = title
        self._done: bool = False
        self._curr_menu: TUIMenu = main_menu
        self._prev_menu = None
        self._next_menu = None

    def execute(self) -> None:
        """Execute the terminal menu UI flow."""

        self._prepare_render()

        while not self._done:
            if self._curr_menu:
                self._next_menu = self._curr_menu.execute()
                if self._next_menu:
                    self._change_menu(
                        self._next_menu
                        if isinstance(self._next_menu, TUIMenu)
                        else next((menu for menu in self._next_menu if menu), None)
                    )
                else:
                    self._done = True
            else:
                self._done = True

        Terminal.restore()

    def _prepare_render(self, auto_wrap: bool = True, show_cursor: bool = False, clear_screen: bool = True) -> None:
        """Prepare the screen for renderization."""
        Terminal.set_auto_wrap(auto_wrap)
        Terminal.set_show_cursor(show_cursor)
        if clear_screen:
            self.SCREEN.clear()
        self.SCREEN.cursor.save()

    def _change_menu(self, new_menu: TUIMenu) -> None:
        """Change the current menu and keep track about the previous one.
        :param new_menu: the menu to be changed to.
        """
        self._prev_menu = self._curr_menu
        self._curr_menu = new_menu
