"""The top of the command line: version, help and the error wrapper."""

from __future__ import annotations

from pathlib import Path

import click
from click.testing import CliRunner

from scowbox import __version__
from scowbox.cli.main import cli, run
from scowbox.errors import RuleError


def test_version_prints_the_package_version() -> None:
    result = CliRunner().invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_about_says_what_the_program_is_for() -> None:
    result = CliRunner().invoke(cli, ["about"])
    assert result.exit_code == 0
    assert "maintenance dredging" in result.output


def test_the_book_option_carries_into_the_context() -> None:
    seen: dict[str, str] = {}

    @cli.command("peek")
    @click.pass_context
    def peek(ctx: click.Context) -> None:
        seen.update(ctx.obj)

    try:
        CliRunner().invoke(cli, ["--book", "/tmp/other.sqlite3", "peek"], obj={})
        assert seen["book"] == "/tmp/other.sqlite3"
    finally:
        del cli.commands["peek"]


def test_the_book_defaults_to_the_working_directory() -> None:
    result = CliRunner().invoke(cli, ["--help"])
    assert "scowbox.sqlite3" in result.output


def test_a_domain_error_becomes_a_message_and_a_status(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def blow_up(**_: object) -> None:
        raise RuleError("closed window")

    monkeypatch.setattr(cli, "main", blow_up)
    assert run() == 2


def test_a_click_error_keeps_its_own_status(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def blow_up(**_: object) -> None:
        raise click.UsageError("no such reach")

    monkeypatch.setattr(cli, "main", blow_up)
    assert run() == 2


def test_an_abort_is_reported_as_one(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def blow_up(**_: object) -> None:
        raise click.exceptions.Abort

    monkeypatch.setattr(cli, "main", blow_up)
    assert run() == 1


def test_a_clean_run_reports_nothing(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(cli, "main", lambda **_: None)
    assert run() == 0


def test_find_says_what_an_identifier_names(tmp_path: Path) -> None:
    from tests.cli.runner import a_book

    run = a_book(tmp_path)
    run(
        "reach", "add", "RCH-012", "Lower Range",
        "--begin", "100+00", "--end", "140+00", "--bottom", "400", "--depth", "42",
    )  # fmt: skip
    assert "RCH-012 Lower Range" in run("find", "RCH-012")


def test_find_fails_on_something_that_is_nothing(tmp_path: Path) -> None:
    from tests.cli.runner import a_book

    a_book(tmp_path)("find", "nothing at all", ok=False)
