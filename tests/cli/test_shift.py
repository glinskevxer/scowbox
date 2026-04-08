"""``scowbox shift`` logs work and sorts the time lost."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.cli.runner import Book, a_book


@pytest.fixture
def run(tmp_path: Path) -> Book:
    made = a_book(tmp_path)
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
    fresh = a_book(tmp_path, "empty.sqlite3")
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


SHIFT_HEAD = "shift,dredge,reach,day,from,to"
STOP_HEAD = "shift,from,to,reason,note"


def a_log(tmp_path: Path, *rows: str) -> str:
    where = tmp_path / "shifts.csv"
    where.write_text(SHIFT_HEAD + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
    return str(where)


def a_stop_file(tmp_path: Path, *rows: str) -> str:
    where = tmp_path / "stops.csv"
    where.write_text(STOP_HEAD + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
    return str(where)


def test_a_log_loads_its_shifts(run: Book, tmp_path: Path) -> None:
    log = a_log(tmp_path, "SH-00030,DR-003,RCH-012,2026-03-19,06:00,18:00")
    out = run("shift", "load", log)
    assert "1 shifts loaded, 0 interruptions" in out
    assert "SH-00030" in run("shift", "list")


def test_the_interruptions_load_with_it(run: Book, tmp_path: Path) -> None:
    log = a_log(tmp_path, "SH-00030,DR-003,RCH-012,2026-03-19,06:00,18:00")
    stops = a_stop_file(tmp_path, "SH-00030,09:00,11:00,weather,squall")
    out = run("shift", "load", log, "--stops", stops)
    assert "1 shifts loaded, 1 interruptions" in out
    assert "10.0 effective" in run("shift", "list")


def test_a_line_that_will_not_read_is_counted(run: Book, tmp_path: Path) -> None:
    log = a_log(
        tmp_path,
        "SH-00030,DR-003,RCH-012,2026-03-19,06:00,18:00",
        "SH-30,DR-003,RCH-012,2026-03-19,06:00,18:00",
    )
    out = run("shift", "load", log)
    assert "1 lines would not read" in out


def test_a_row_the_book_refuses_is_counted(run: Book, tmp_path: Path) -> None:
    log = a_log(tmp_path, "SH-00021,DR-003,RCH-012,2026-03-19,06:00,18:00")
    out = run("shift", "load", log)
    assert "1 rows the book refused" in out


def test_the_refused_rows_can_be_listed(run: Book, tmp_path: Path) -> None:
    log = a_log(tmp_path, "SH-30,DR-003,RCH-012,2026-03-19,06:00,18:00")
    out = run("shift", "load", log, "--show-refused")
    assert "line 2:" in out


def test_a_log_for_a_dredge_that_is_not_there_is_refused(run: Book, tmp_path: Path) -> None:
    log = a_log(tmp_path, "SH-00030,DR-009,RCH-012,2026-03-19,06:00,18:00")
    out = run("shift", "load", log)
    assert "0 shifts loaded" in out
    assert "1 rows the book refused" in out
