"""The printing check, on this package and on a renderer that prints."""

from __future__ import annotations

from pathlib import Path

import pytest

from scowbox.tools.check_printing import findings, main
from scowbox.tools.scan import parse


def a_module(tmp_path: Path, body: str, package: str = "report") -> list[str]:
    where = tmp_path / package
    where.mkdir(exist_ok=True)
    module = where / "sample.py"
    module.write_text('"""A sample module for the check."""\n' + body, encoding="utf-8")
    return findings([parse(module, tmp_path)])


def test_this_package_has_nothing_to_report() -> None:
    assert findings() == []


def test_the_check_exits_clean(capsys: pytest.CaptureFixture[str]) -> None:
    assert main() == 0
    assert "check_printing" in capsys.readouterr().out


def test_a_print_outside_the_command_line_is_found(tmp_path: Path) -> None:
    found = a_module(tmp_path, "print('hello')\n")
    assert "calls print()" in found[0]


def test_an_echo_outside_the_command_line_is_found(tmp_path: Path) -> None:
    found = a_module(tmp_path, "import click\n\nclick.echo('hello')\n")
    assert "calls click.echo()" in found[0]


def test_a_write_to_stdout_is_found(tmp_path: Path) -> None:
    found = a_module(tmp_path, "import sys\n\nsys.stdout.write('hello')\n")
    assert "sys.stdout.write()" in found[0]


def test_a_write_to_a_file_is_not(tmp_path: Path) -> None:
    found = a_module(
        tmp_path,
        "def go(handle):\n    handle.write('hello')\n",
    )
    assert found == []


def test_the_command_line_is_allowed_to_print(tmp_path: Path) -> None:
    found = a_module(tmp_path, "import click\n\nclick.echo('hello')\n", "cli")
    assert found == []


def test_the_check_tools_are_allowed_to_print(tmp_path: Path) -> None:
    found = a_module(tmp_path, "print('hello')\n", "tools")
    assert found == []


def test_returning_lines_is_fine(tmp_path: Path) -> None:
    found = a_module(tmp_path, "def go() -> list[str]:\n    return ['a line']\n")
    assert found == []
