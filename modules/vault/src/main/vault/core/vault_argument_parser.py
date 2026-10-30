"""Do not echo rejected arguments, which may contain an old positional password."""

import argparse

from hspylib.modules.application.argparse.argument_parser import HSArgumentParser


class VaultArgumentParser(HSArgumentParser):
    def error(self, message):
        super().error("Invalid arguments. Passwords must be entered at the protected prompt.")

    def _check_value(self, action, value):
        if action.choices is not None and value not in action.choices:
            raise argparse.ArgumentError(action, "Invalid argument value")
