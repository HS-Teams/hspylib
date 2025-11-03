#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import unittest
from pathlib import Path
from typing import List, Optional, Sequence, Tuple
from unittest import mock

TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

from _test_setup import setup_test_environment

setup_test_environment()

from clitt.core.term.terminal import Terminal
from clitt.utils.git_utils import GitTools
from hspylib.modules.application.exit_status import ExitStatus


TerminalResponse = Tuple[str, str, ExitStatus]


class TestGitToolsCommands(unittest.TestCase):
    def _capture_shell_exec(self, responses: Optional[Sequence[TerminalResponse]] = None):
        captured: List[str] = []
        iterator = iter(responses or [("", "", ExitStatus.SUCCESS)])

        def _fake_shell_exec(cmd_line: str, **_kwargs):
            captured.append(cmd_line)
            try:
                return next(iterator)
            except StopIteration:
                return "", "", ExitStatus.SUCCESS

        return captured, _fake_shell_exec

    def test_top_level_dir_command(self):
        captured, fake_exec = self._capture_shell_exec()
        with mock.patch.object(Terminal, "shell_exec", side_effect=fake_exec):
            GitTools.top_level_dir()

        self.assertEqual(["git rev-parse --show-toplevel"], captured)

    def test_current_branch_command(self):
        captured, fake_exec = self._capture_shell_exec()
        with mock.patch.object(Terminal, "shell_exec", side_effect=fake_exec):
            GitTools.current_branch()

        self.assertEqual(["git symbolic-ref --short HEAD"], captured)

    def test_changelog_range_command(self):
        captured, fake_exec = self._capture_shell_exec()
        with mock.patch.object(Terminal, "shell_exec", side_effect=fake_exec):
            GitTools.changelog("v1.0.0", "v2.0.0")

        expected = [
            "git log --oneline --pretty='format:%h %ad %s' --date=short v1.0.0^..v2.0.0^"
        ]
        self.assertEqual(expected, captured)

    def test_unreleased_uses_latest_tag_in_log_range(self):
        responses = [("v2.3.4", "", ExitStatus.SUCCESS), ("", "", ExitStatus.SUCCESS)]
        captured, fake_exec = self._capture_shell_exec(responses)
        with mock.patch.object(Terminal, "shell_exec", side_effect=fake_exec):
            GitTools.unreleased()

        self.assertEqual(
            [
                "git describe --tags --abbrev=0 HEAD^",
                "git log --oneline --pretty='format:%h %ad %s' --date=short 'v2.3.4'..HEAD",
            ],
            captured,
        )

    def test_release_date_command(self):
        captured, fake_exec = self._capture_shell_exec()
        with mock.patch.object(Terminal, "shell_exec", side_effect=fake_exec):
            GitTools.release_date("v1.2.3")

        expected = ["git log -1 --pretty='format:%ad' --date=short v1.2.3"]
        self.assertEqual(expected, captured)

    def test_tag_list_command(self):
        captured, fake_exec = self._capture_shell_exec()
        with mock.patch.object(Terminal, "shell_exec", side_effect=fake_exec):
            GitTools.tag_list()

        expected = [
            "git log --tags --simplify-by-decoration --pretty='format:%ci %d'"
        ]
        self.assertEqual(expected, captured)

    def test_create_tag_with_custom_description(self):
        captured, fake_exec = self._capture_shell_exec()
        with mock.patch.object(Terminal, "shell_exec", side_effect=fake_exec):
            GitTools.create_tag("1.2.3", commit_id="abc123", description="Release 1.2.3")

        expected = ["git tag -a v1.2.3 abc123 -m 'Release 1.2.3'"]
        self.assertEqual(expected, captured)

    def test_search_logs_with_regex(self):
        captured, fake_exec = self._capture_shell_exec()
        with mock.patch.object(Terminal, "shell_exec", side_effect=fake_exec):
            GitTools.search_logs(filter_by="^(feat|fix)")

        expected = [
            "git log --grep='^(feat|fix)' --pretty=format:'%h %ad %s' --date=short"
        ]
        self.assertEqual(expected, captured)

    def test_show_file_at_commit(self):
        captured, fake_exec = self._capture_shell_exec()
        with mock.patch.object(Terminal, "shell_exec", side_effect=fake_exec):
            GitTools.show_file("path/to/file.txt", commit_id="123abc")

        self.assertEqual(["git show 123abc:path/to/file.txt"], captured)


if __name__ == "__main__":
    unittest.main()
