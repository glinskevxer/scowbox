"""The help check, on the real command tree and on a command with none."""

from __future__ import annotations

import click
import pytest

from scowbox.cli.main import cli
from scowbox.tools.check_help import commands, findings, main, walk


def test_this_command_line_passes() -> None:
    assert findings() == []


def test_the_check_exits_clean(capsys: pytest.CaptureFixture[str]) -> None:
    assert main() == 0
    assert "check_help" in capsys.readouterr().out


def test_the_tree_has_a_lot_of_commands() -> None:
    assert commands() > 30


def _tree() -> click.Group:
    @click.group("sample")
    def sample() -> None:
        """A sample group for the check."""

    @sample.command("go")
    @click.option("--fast", help="Go quickly.")
    def go(fast: str) -> None:
        """Go and do the thing."""

    return sample


def test_the_walk_names_the_path_a_user_would_type() -> None:
    paths = [path for path, _ in walk(_tree())]
    assert paths == ["sample", "sample go"]


def test_the_real_tree_is_walked_from_the_top() -> None:
    paths = [path for path, _ in walk(cli)]
    assert paths[0] == "cli"
    assert "cli reach add" in paths


def test_a_command_with_no_help_is_found() -> None:
    @click.group("sample")
    def sample() -> None:
        """A sample group for the check."""

    @sample.command("go")
    def go() -> None:
        pass

    assert findings(sample) == ["sample go has no help"]


def test_a_command_with_two_words_of_help_is_too_thin() -> None:
    @click.group("sample")
    def sample() -> None:
        """A sample group for the check."""

    @sample.command("go")
    def go() -> None:
        """Go now."""

    assert "under 3 words" in findings(sample)[0]


def test_an_option_with_no_help_is_found() -> None:
    @click.group("sample")
    def sample() -> None:
        """A sample group for the check."""

    @sample.command("go")
    @click.option("--fast")
    def go(fast: str) -> None:
        """Go and do the thing."""

    assert findings(sample) == ["sample go option --fast has no help"]


def test_an_argument_needs_no_help() -> None:
    @click.group("sample")
    def sample() -> None:
        """A sample group for the check."""

    @sample.command("go")
    @click.argument("where")
    def go(where: str) -> None:
        """Go and do the thing."""

    assert findings(sample) == []


def test_a_clean_tree_reports_nothing() -> None:
    assert findings(_tree()) == []
