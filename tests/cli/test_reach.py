"""``scowbox reach`` writes and reads the channel through a real book."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from scowbox.cli.main import cli


class Book:
    """A runner bound to one book file, so every call sees the same project."""

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


ADD = [
    "reach",
    "add",
    "RCH-012",
    "Lower Range",
    "--begin",
    "100+00",
    "--end",
    "140+00",
    "--bottom",
    "400",
    "--depth",
    "42",
    "--advance",
    "2",
    "--overdepth",
    "2",
]


def test_init_makes_a_book(tmp_path: Path) -> None:
    where = tmp_path / "new.sqlite3"
    Book(where)("init")
    assert where.exists()


def test_a_command_against_a_book_that_is_not_there_fails(tmp_path: Path) -> None:
    out = Book(tmp_path / "nothing.sqlite3")("reach", "list", ok=False)
    assert "no book" in out or out == ""


def test_an_added_reach_shows_up_in_the_list(run: Book) -> None:
    run(*ADD)
    assert "RCH-012" in run("reach", "list")


def test_an_empty_book_says_so(run: Book) -> None:
    assert "no reaches" in run("reach", "list")


def test_show_prints_the_three_depths(run: Book) -> None:
    run(*ADD)
    out = run("reach", "show", "RCH-012")
    assert "authorized 42.00 ft" in out
    assert "required   44.00 ft" in out
    assert "pay        46.00 ft" in out


def test_show_reports_the_length(run: Book) -> None:
    run(*ADD)
    assert "4,000 ft" in run("reach", "show", "RCH-012")


def test_the_same_reach_twice_is_refused(run: Book) -> None:
    run(*ADD)
    run(*ADD, ok=False)


def test_a_group_filters_the_list(run: Book) -> None:
    run(*ADD)
    run(*ADD[:2], "RCH-014", "Entrance", *ADD[4:], "--group", "entrance")
    out = run("reach", "list", "--group", "entrance")
    assert "RCH-014" in out
    assert "RCH-012" not in out


def test_a_removed_reach_leaves_the_list(run: Book) -> None:
    run(*ADD)
    run("reach", "remove", "RCH-012")
    assert "no reaches" in run("reach", "list")


def test_counts_reports_the_reach_table(run: Book) -> None:
    run(*ADD)
    assert "reach" in run("counts")


def test_a_reach_with_a_bad_station_is_refused(run: Book) -> None:
    run(*ADD[:6], "1400", *ADD[7:], ok=False)
