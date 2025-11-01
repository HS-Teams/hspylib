#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
   @project: HsPyLib
   @package: hspylib.core.tools
      @file: commons.py
   @created: Tue, 4 May 2021
    @author: <B>H</B>ugo <B>S</B>aporetti <B>J</B>unior
      @site: https://github.com/yorevs/hspylib
   @license: MIT - Please refer to <https://opensource.org/licenses/MIT>

   Copyright·(c)·2024,·HSPyLib
"""
import inspect
import logging as log
import os
import pathlib
import signal
import sys
from datetime import timedelta
from typing import Any, Callable, Iterable, Optional, Set, Tuple, Type, Union, Literal, TypeAlias

from hspylib.core.constants import TRUE_VALUES
from hspylib.core.enums.charset import Charset
from hspylib.core.preconditions import check_argument, check_not_none
from hspylib.modules.cli.vt100.vt_code import VtCode
from hspylib.modules.cli.vt100.vt_color import VtColor
from rich.console import Console
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.text import Text

# pylint: disable=consider-using-f-string
DEFAULT_FILE_LOG_FMT = "{} {} [{}] {} (@Line:{}) {} : {}".format(
    "%(asctime)s.%(msecs)03d",
    "%(levelname)-7.7s",
    "%(threadName)12.12s",
    "%(process)-5d",
    "%(lineno)05d",
    "%(filename)-30.30s",
    "%(message)s",
)

# pylint: disable=consider-using-f-string
DEFAULT_CONSOLE_LOG_FMT = "{} [{}] (@Line:{}) {} : {}".format(
    "%(levelname)-7.7s", "%(threadName)12.12s", "%(lineno)05d", "%(filename)-30.30s", "%(message)s"
)

LOG_DATE_FMT = "%Y-%m-%d %H:%M:%S"

console_out = Console(force_terminal=True, soft_wrap=False)

console_err = Console(force_terminal=True, soft_wrap=False, stderr=True)

FileMode: TypeAlias = Literal[
    # Modes for reading
    "r", "rb", "rt", "r+", "r+b",
    # Modes for writing
    "w", "wb", "wt", "w+", "w+b",
    # Modes for appending
    "a", "ab", "at", "a+", "a+b"
]


def log_init(
    filename: str | None = None,
    filemode: FileMode = "a",
    level: int = log.NOTSET,
    file_format: str = DEFAULT_FILE_LOG_FMT,
    console_format: str = DEFAULT_CONSOLE_LOG_FMT,
    clear_handlers: bool = True,
    console_enable: bool = False,
    rich_logging: bool = False,
) -> bool:
    """Initialize the system logger"""

    # if someone tried to log something before log_init is called, Python creates a default handler that is going to
    # mess our logs. Remove handlers if there is any.
    root, handlers = log.getLogger(), set()

    if clear_handlers:
        if root.handlers:
            for handler in root.handlers:
                handler.close()
                root.removeHandler(handler)

    if filename:
        if not os.path.exists(filename):
            touch_file(filename)
        touch_file(filename)
        file_formatter = log.Formatter(file_format, LOG_DATE_FMT)
        file_handler = log.FileHandler(filename=filename, mode=filemode)
        file_handler.setFormatter(file_formatter)
        handlers.add(file_handler)

    if rich_logging or console_enable or (filename and not os.path.exists(filename)):
        if rich_logging:
            # Use rich logger.
            console_handler = RichHandler(
                level=level,
                locals_max_length=0,
                locals_max_string=0,
                rich_tracebacks=True)
        else:
            console_formatter = log.Formatter(console_format, LOG_DATE_FMT)
            console_handler = log.StreamHandler(sys.stdout)
            console_handler.setFormatter(console_formatter)
            handlers.add(console_handler)
        handlers.add(console_handler)

    log.basicConfig(level=level, handlers=handlers)

    return filename is not None if os.path.exists(filename or "") else console_enable


def is_debugging() -> bool:
    """Whether the program is running under debug mode."""
    for frame in inspect.stack():
        if frame[1].endswith("pydevd.py"):
            return True
    return False


def dirname(filepath: str) -> Optional[str]:
    """Extract the directory of the specified filepath."""
    return os.path.dirname(os.path.realpath(filepath))


def root_dir() -> str:
    """Get the application's root directory."""
    return sys.path[0]


def parent_path(filepath: str) -> pathlib.Path:
    """Extract the parent Path of the file."""
    return pathlib.Path(filepath).parent


def sysout(*objs: Any, end: str = os.linesep, markdown: bool = False) -> None:
    """Print the unicode input_string decoding vt100 placeholders.
    :param objs: values to be printed to sys.stdout.
    :param end: string appended after the last value, default a newline.
    :param markdown: whether to print a markdown render.
    """
    if objs is not None:
        def _sysout_format(obj: Any) -> Union[Text | Markdown]:
            text = str(obj) if obj is not None else ""
            text = VtColor.colorize(VtCode.decode(text))
            return Text(text) if not markdown else Markdown(text)

        list(map_many(objs, _sysout_format, lambda s: console_out.print(s, end="")))
        console_out.print("", end=end)


def syserr(*objs: Any, end: str = os.linesep, markdown: bool = False) -> None:
    """Print the unicode input_string decoding vt100 placeholders.
    :param objs: values to be printed to sys.stderr.
    :param end: string appended after the last value, default a newline.
    :param markdown: whether to print markdown.
    """
    if objs is not None:
        def _syserr_format(obj: Any) -> Union[str | Markdown]:
            text = VtColor.strip_colors(str(obj)) if obj is not None else ""
            text = VtColor.colorize(VtCode.decode(f"%RED%{text}%NC%"))
            return Text(text) if not markdown else Markdown(text)

        list(map_many(objs, _syserr_format, lambda s: console_err.print(s, end="")))
        console_err.print("", end=end)


def hook_exit_signals(handler: Callable) -> None:
    """Hook common exit signals and set proper handlers for them
    :param handler a Callable to handle the exit signals
    """
    check_argument(handler is not None and isinstance(handler, Callable))
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGHUP, handler)
    signal.signal(signal.SIGABRT, handler)


def class_attribute_names(clazz: Type) -> Optional[Tuple]:
    """Retrieve the names of the attributes defined by a class.

    The attribute names are inferred from the ``__init__`` signature without instantiating the class,
    which allows classes that require initialization arguments to be inspected safely.

    :param clazz: The class whose attribute names should be retrieved.
    :return: A tuple containing the attribute names in the order they appear in ``__init__`` or ``None``
        when ``clazz`` is ``None``.
    """
    if not clazz:
        return None

    try:
        signature = inspect.signature(clazz.__init__)
    except (TypeError, ValueError):
        return tuple()

    return tuple(
        name
        for name, param in signature.parameters.items()
        if name != "self" and param.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
    )


def class_attribute_values(instance: dict) -> Optional[Tuple]:
    """Retrieve all attribute values of the class
    :param instance: The class to retrieve the attribute values
    """
    return tuple(instance.values()) if instance else None


def to_bool(string: Any, true_values: Set[str] = None) -> bool:
    """Convert a string to boolean
    :param string: The string to be converted
    :param true_values: The list of strings that will become True value
    """
    return string is not None and str(string).lower() in (true_values or TRUE_VALUES)


def map_many(iterable: Iterable, function: Callable, *functions) -> Optional[map]:
    """Maps multiple functions to the same iterable
    :param iterable The iterable to map
    :param function The first function to be mapped
    :param functions the other functions to be mapped
    """
    check_not_none((iterable, function))
    if functions:
        # Recursively map all functions
        return map_many(map(function, iterable), *functions)

    # Map the single function
    return map(function, iterable)


def safe_delete_file(filename: str, on_not_found_except: bool = False) -> bool:
    """Delete the file specified by filename. If the file is not found, raises an exception if on_not_found_except is
    True; otherwise return False.
    :param filename: the name of the file to be checked
    :param on_not_found_except: boolean parameter to raise an exception if the file is not found.
    """
    if os.path.exists(filename):
        os.remove(filename)
    else:
        if on_not_found_except:
            raise FileNotFoundError(f"File was not found on the system: {filename}")
        return False

    return True


def file_is_not_empty(filename: str) -> bool:
    """Check whether the file is empty or not.
    :param filename: the name of the file to be modified. If the file does not exist; return False
    """
    return os.path.exists(filename) and os.stat(filename).st_size > 0


def touch_file(filename: str, encoding: str = Charset.UTF_8.val) -> None:
    """Change file modification time
    :param filename: the name of the file to be modified
    :param encoding: the file encoding
    """
    with open(filename, "a", encoding=encoding):
        os.utime(filename, None)


def human_readable_bytes(size_in_bytes: int) -> Tuple[str, str]:
    """Return a Human readable bytes and unit
    :param size_in_bytes: the size to be formatted
    """

    byte_size = float(size_in_bytes)
    kb, mb, gb, tb = 2 ** 10, 2 ** 20, 2 ** 30, 2 ** 40

    if 0 <= byte_size <= kb:
        ret_val = f"{byte_size:3.2f}"
        ret_unit = "[B]"
    elif kb < byte_size <= mb:
        ret_val = f"{byte_size / kb:3.2f}"
        ret_unit = "[Kb]"
    elif mb < byte_size <= gb:
        ret_val = f"{byte_size / mb:3.2f}"
        ret_unit = "[Mb]"
    elif gb < byte_size <= tb:
        ret_val = f"{byte_size / gb:3.2f}"
        ret_unit = "[Gb]"
    else:
        ret_val = f"{byte_size / tb:3.2f}"
        ret_unit = "[Tb]"

    return ret_val, ret_unit


def human_readable_time(time_microseconds: int) -> str:
    """Return a Human readable formatted time using format: HH:MM:SS.uuuuuu
    :param time_microseconds: the time to be formatted
    """
    delta = timedelta(microseconds=time_microseconds)
    total_seconds = delta.seconds
    seconds = total_seconds % 60
    minutes = total_seconds / 60 % 60
    hours = total_seconds / 3600
    microseconds = delta.microseconds

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{microseconds:06d}"
