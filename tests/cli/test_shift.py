"""``scowbox shift`` logs work and sorts the time lost."""

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
    made(
        "reach", "add", "RCH-012", "Lower Range",
        "--begin", "100+00", "--end", "140+00", "--bottom", "400", "--depth", "42",
    )  # fmt: skip
    made(
        "shift", "dredge", "DR-003", "Cherokee",
        "--plant", "mechanical", "--operator", "Norfolk Dredging",
    )  # fmt: skip
    made(
        "shift", "log", "SH-00021",
        "--dredge", "DR-003", "--reach", "RCH-012",
        "--on", "2025-06-04", "--from", "06:00", "--to", "18:00",
    )  # fmt: skip
    return made


def test_a_dredge_is_described_when_it_is_added(run: Book) -> None:
    out = run(
        "shift", "dredge", "DR-001", "Currituck",
        "--plant", "hopper", "--operator", "USACE",
    )  # fmt: skip
    assert out.strip() == "DR-001 Currituck, hopper, USACE"


def test_a_logged_shift_reports_its_hours(run: Book) -> None:
    out = run(
        "shift", "log", "SH-00022",
        "--dredge", "DR-003", "--reach", "RCH-012",
        "--on", "2025-06-05", "--from", "06:00", "--to", "18:00",
    )  # fmt: skip
    assert "12 hours" in out


def test_a_shift_on_a_dredge_that_is_not_there_is_refused(run: Book) -> None:
    run(
        "shift", "log", "SH-00023",
        "--dredge", "DR-009", "--reach", "RCH-012",
        "--on", "2025-06-05", "--from", "06:00", "--to", "18:00", ok=False,
    )  # fmt: skip


def test_shifts_are_listed_with_their_effective_hours(run: Book) -> None:
    out = run("shift", "list")
    assert "SH-00021" in out
    assert "12.0 effective" in out


def test_an_empty_book_says_so(tmp_path: Path) -> None:
    fresh = Book(tmp_path / "empty.sqlite3")
    fresh("init")
    assert "no shifts" in fresh("shift", "list")


def test_an_interruption_says_how_it_is_treated(run: Book) -> None:
    out = run(
        "shift", "stop", "SH-00021",
        "--from", "09:00", "--to", "11:00", "--reason", "weather",
    )  # fmt: skip
    assert "2 hours weather" in out
    assert "allowable" in out


def test_a_breakdown_is_the_contractor_s(run: Book) -> None:
    out = run(
        "shift", "stop", "SH-00021",
        "--from", "09:00", "--to", "11:00", "--reason", "breakdown",
    )  # fmt: skip
    assert "contractor" in out


def test_two_interruptions_that_overlap_are_refused(run: Book) -> None:
    run("shift", "stop", "SH-00021", "--from", "09:00", "--to", "11:00", "--reason", "weather")
    run(
        "shift", "stop", "SH-00021",
        "--from", "10:00", "--to", "12:00", "--reason", "weather", ok=False,
    )  # fmt: skip


def test_the_time_report_sorts_downtime_three_ways(run: Book) -> None:
    run("shift", "stop", "SH-00021", "--from", "06:00", "--to", "11:00", "--reason", "weather")
    run(
        "shift", "stop", "SH-00021",
        "--from", "13:00", "--to", "14:00", "--reason", "channel traffic",
    )  # fmt: skip
    out = run("shift", "time", "--from", "2025-06-01", "--to", "2025-06-30")
    assert "allowable  6.00 hours" in out
    assert "standby    1.00 hours" in out
    assert "contractor 0.00 hours" in out


def test_the_time_report_credits_a_day_rained_off(run: Book) -> None:
    run("shift", "stop", "SH-00021", "--from", "06:00", "--to", "13:00", "--reason", "weather")
    out = run("shift", "time", "--from", "2025-06-01", "--to", "2025-06-30")
    assert "days earned  1" in out
    assert "2025-06-04" in out


def test_a_stricter_share_credits_nothing(run: Book) -> None:
    run("shift", "stop", "SH-00021", "--from", "06:00", "--to", "13:00", "--reason", "weather")
    out = run("shift", "time", "--from", "2025-06-01", "--to", "2025-06-30", "--share", "0.9")
    assert "days earned  0" in out
