"""``scowbox window`` answers what governs a reach on a day."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from scowbox.cli.main import cli


class Book:
    def __init__(self, path: Path) -> None:
        self.path = str(path)
        self.runner = CliRunner()

    def __call__(self, *args: str, ok: bool = True) -> str:
        result = self.runner.invoke(cli, ["--book", self.path, *args], obj={})
        if ok:
            assert result.exit_code == 0, result.output + str(result.exception)
        else:
            assert result.exit_code != 0
        return result.output


@pytest.fixture
def run(tmp_path: Path) -> Book:
    made = Book(tmp_path / "book.sqlite3")
    made("init")
    return made


TURTLE = [
    "window", "add", "loggerhead",
    "--from", "2025-05-01", "--to", "2025-11-30",
    "--restriction", "closed", "--authority", "NMFS",
]  # fmt: skip


def test_an_added_window_describes_itself(run: Book) -> None:
    out = run(*TURTLE)
    assert "loggerhead (NMFS): 2025-05-01 to 2025-11-30, all reaches, closed" in out


def test_an_empty_book_says_so(run: Book) -> None:
    assert "no windows" in run("window", "list")


def test_windows_are_listed_with_their_length(run: Book) -> None:
    run(*TURTLE)
    assert "(214 days)" in run("window", "list")


def test_a_day_inside_a_closure_is_closed(run: Book) -> None:
    run(*TURTLE)
    out = run("window", "on", "2025-07-01", "RCH-012")
    assert "RCH-012 on 2025-07-01: closed" in out
    assert "loggerhead (NMFS) closed" in out
    assert "opens 2025-12-01" in out


def test_a_day_outside_every_window_is_open(run: Book) -> None:
    run(*TURTLE)
    out = run("window", "on", "2025-04-01", "RCH-012")
    assert "open" in out
    assert "opens" not in out


def test_a_window_on_one_reach_does_not_bind_another(run: Book) -> None:
    run(*TURTLE, "--reach", "RCH-014")
    assert "closed" in run("window", "on", "2025-07-01", "RCH-014")
    assert "open" in run("window", "on", "2025-07-01", "RCH-012")


def test_the_stricter_window_governs(run: Book) -> None:
    run(*TURTLE)
    run(
        "window", "add", "oyster",
        "--from", "2025-06-01", "--to", "2025-08-31",
        "--restriction", "observer required", "--authority", "NCDMF",
    )  # fmt: skip
    out = run("window", "on", "2025-07-01", "RCH-012")
    assert "RCH-012 on 2025-07-01: closed" in out
    assert "oyster" in out


def test_the_same_window_twice_is_refused(run: Book) -> None:
    run(*TURTLE)
    run(*TURTLE, ok=False)
