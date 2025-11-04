#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Test utilities to prepare the environment for unit tests."""

from pathlib import Path
from types import ModuleType
import sys


def _stub_cursor_and_screen() -> None:
    if "clitt.core.term.cursor" not in sys.modules:
        cursor_module = ModuleType("clitt.core.term.cursor")

        class _Cursor:  # pragma: no cover - runtime stub
            INSTANCE = None

            def __init__(self):
                type(self).INSTANCE = self
                self._position = (0, 0)

            @property
            def position(self):
                return self._position

            @position.setter
            def position(self, value):
                self._position = value

            def write(self, *_, **__):
                return self._position

            def track(self):
                return self._position

            def home(self):
                self._position = (0, 0)
                return self._position

            def erase(self, *_):
                return self._position

            def move(self, *_):
                return self._position

        cursor_module.Cursor = _Cursor
        sys.modules["clitt.core.term.cursor"] = cursor_module

    if "clitt.core.term.screen" not in sys.modules:
        screen_module = ModuleType("clitt.core.term.screen")

        class _Screen:  # pragma: no cover - runtime stub
            INSTANCE = None

            def __init__(self):
                type(self).INSTANCE = self
                self.cursor = sys.modules["clitt.core.term.cursor"].Cursor.INSTANCE or \
                    sys.modules["clitt.core.term.cursor"].Cursor()
                self._alternate = False

            def clear(self):
                pass

            @property
            def alternate(self) -> bool:
                return self._alternate

            @alternate.setter
            def alternate(self, enable: bool) -> None:
                self._alternate = enable

        screen_module.Screen = _Screen
        screen_module.screen = screen_module.Screen()
        sys.modules["clitt.core.term.screen"] = screen_module


def setup_test_environment() -> None:
    """Configure sys.path and provide runtime stubs for optional dependencies."""
    test_dir = Path(__file__).resolve().parent
    clitt_src_main = test_dir.parent / "main"
    hspylib_src_main = test_dir.parent.parent.parent / "hspylib" / "src" / "main"
    for path in (clitt_src_main, hspylib_src_main):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))

    _stub_cursor_and_screen()

    if "rich" not in sys.modules:
        sys.modules["rich"] = ModuleType("rich")

    if "rich.console" not in sys.modules:
        class _Console:  # pragma: no cover - runtime stub
            def __init__(self, *args, **kwargs):
                pass

            def print(self, *args, **kwargs):
                pass

        console_module = ModuleType("rich.console")
        console_module.Console = _Console
        sys.modules["rich.console"] = console_module

    if "rich.logging" not in sys.modules:
        class _RichHandler:  # pragma: no cover - runtime stub
            def __init__(self, *args, **kwargs):
                pass

        logging_module = ModuleType("rich.logging")
        logging_module.RichHandler = _RichHandler
        sys.modules["rich.logging"] = logging_module

    if "rich.markdown" not in sys.modules:
        class _Markdown:  # pragma: no cover - runtime stub
            def __init__(self, *args, **kwargs):
                pass

        markdown_module = ModuleType("rich.markdown")
        markdown_module.Markdown = _Markdown
        sys.modules["rich.markdown"] = markdown_module

    if "rich.text" not in sys.modules:
        class _Text:  # pragma: no cover - runtime stub
            def __init__(self, *args, **kwargs):
                pass

        text_module = ModuleType("rich.text")
        text_module.Text = _Text
        sys.modules["rich.text"] = text_module

    if "toml" not in sys.modules:
        toml_module = ModuleType("toml")

        def _loads(*args, **kwargs):  # pragma: no cover - runtime stub
            return {}

        def _dumps(*args, **kwargs):  # pragma: no cover - runtime stub
            return ""

        toml_module.load = _loads
        toml_module.loads = _loads
        toml_module.dump = _dumps
        toml_module.dumps = _dumps
        sys.modules["toml"] = toml_module

    if "yaml" not in sys.modules:
        yaml_module = ModuleType("yaml")

        def _yaml_load(*args, **kwargs):  # pragma: no cover - runtime stub
            return {}

        def _yaml_dump(*args, **kwargs):  # pragma: no cover - runtime stub
            return ""

        yaml_module.safe_load = _yaml_load
        yaml_module.safe_dump = _yaml_dump
        yaml_module.load = _yaml_load
        yaml_module.dump = _yaml_dump
        sys.modules["yaml"] = yaml_module

    if "getkey" not in sys.modules:
        class _Keys:  # pragma: no cover - runtime stub
            def __getattr__(self, name):
                return name

        getkey_module = ModuleType("getkey")
        getkey_module.keys = _Keys()

        def _getkey(*args, **kwargs):  # pragma: no cover - runtime stub
            return ""

        getkey_module.getkey = _getkey
        sys.modules["getkey"] = getkey_module


__all__ = ["setup_test_environment"]
