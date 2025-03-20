"""``scowbox tide`` loads a download and reads it back."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from scowbox.cli.main import cli

HEAD = "Date Time,Water Level,Sigma,O,F,R,L,Quality"


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


def a_download(where: Path, *rows: str) -> str:
    where.write_text(HEAD + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
    return str(where)


VERIFIED = [
    "2025-03-14 07:00,1.023,0.010,0,0,0,0,v",
    "2025-03-14 07:06,1.610,0.010,0,0,0,0,v",
]


def test_loading_reports_what_was_read_and_what_was_new(run: Book, tmp_path: Path) -> None:
    where = a_download(tmp_path / "g.csv", *VERIFIED)
    assert "2 read, 2 new" in run("tide", "load", "8658120", where)
    assert "2 read, 0 new" in run("tide", "load", "8658120", where)


def test_preliminary_readings_are_called_out(run: Book, tmp_path: Path) -> None:
    where = a_download(tmp_path / "g.csv", *VERIFIED, "2025-03-14 07:12,1.7,0.01,0,0,0,0,p")
    assert "1 preliminary" in run("tide", "load", "8658120", where)


def test_flagged_readings_are_called_out(run: Book, tmp_path: Path) -> None:
    where = a_download(tmp_path / "g.csv", *VERIFIED, "2025-03-14 07:12,1.7,0.01,0,1,0,0,v")
    assert "flat tolerance" in run("tide", "load", "8658120", where)


def test_unreadable_lines_are_counted(run: Book, tmp_path: Path) -> None:
    where = a_download(tmp_path / "g.csv", *VERIFIED, "later,1.7,0.01,0,0,0,0,v")
    assert "1 lines would not read" in run("tide", "load", "8658120", where)


def test_an_empty_book_lists_no_gauges(run: Book) -> None:
    assert "no gauges" in run("tide", "list")


def test_a_loaded_gauge_lists_its_span(run: Book, tmp_path: Path) -> None:
    run("tide", "load", "8658120", a_download(tmp_path / "g.csv", *VERIFIED))
    out = run("tide", "list")
    assert "8658120" in out
    assert "2025-03-14 07:00 to 2025-03-14 07:06" in out


def test_the_height_at_a_moment_is_interpolated(run: Book, tmp_path: Path) -> None:
    run("tide", "load", "8658120", a_download(tmp_path / "g.csv", *VERIFIED))
    out = run("tide", "at", "8658120", "2025-03-14T07:03:00-05:00")
    assert "+1.317 ft" in out


def test_a_moment_the_gauge_did_not_cover_fails(run: Book, tmp_path: Path) -> None:
    run("tide", "load", "8658120", a_download(tmp_path / "g.csv", *VERIFIED))
    run("tide", "at", "8658120", "2025-03-14T12:00:00-05:00", ok=False)
