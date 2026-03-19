"""The tender's shift log, and the day a stop takes."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from scowbox.errors import FieldError
from scowbox.feed.shiftlog import (
    kept_shifts,
    kept_stops,
    parse_files,
    parse_shifts,
    parse_stops,
    refused,
)
from scowbox.model.shift import Reason

SHIFT_HEAD = "shift,dredge,reach,day,from,to"
STOP_HEAD = "shift,from,to,reason,note"
GOOD_SHIFT = [SHIFT_HEAD, "SH-00021,DR-003,RCH-012,2026-03-10,06:00,18:00"]
DAYS = {"SH-00021": dt.date(2026, 3, 10)}


def test_a_clean_shift_file_reads_every_line() -> None:
    reads = parse_shifts(GOOD_SHIFT)
    assert len(kept_shifts(reads)) == 1
    assert refused(reads) == ()


def test_the_fields_land_where_they_belong() -> None:
    shift = kept_shifts(parse_shifts(GOOD_SHIFT))[0]
    assert shift.ident == "SH-00021"
    assert shift.dredge == "DR-003"
    assert shift.day == dt.date(2026, 3, 10)
    assert shift.gross_hours == 12.0


def test_a_bad_identifier_is_refused_by_line() -> None:
    reads = parse_shifts([SHIFT_HEAD, "SH-21,DR-003,RCH-012,2026-03-10,06:00,18:00"])
    assert refused(reads)[0].line == 2
    assert "shift identifier" in str(refused(reads)[0].trouble)


def test_a_day_that_is_not_a_day_is_refused() -> None:
    reads = parse_shifts([SHIFT_HEAD, "SH-00021,DR-003,RCH-012,Tuesday,06:00,18:00"])
    assert "not a day" in str(refused(reads)[0].trouble)


def test_a_shift_that_ends_first_is_refused() -> None:
    reads = parse_shifts([SHIFT_HEAD, "SH-00021,DR-003,RCH-012,2026-03-10,18:00,06:00"])
    assert "ends after it begins" in str(refused(reads)[0].trouble)


def test_a_short_row_says_how_many_fields_it_had() -> None:
    reads = parse_shifts([SHIFT_HEAD, "SH-00021,DR-003"])
    assert "2 fields" in str(refused(reads)[0].trouble)


def test_the_wrong_heading_is_refused_before_anything_is_read() -> None:
    with pytest.raises(FieldError):
        parse_shifts(["a,b,c", "1,2,3"])


def test_an_empty_file_is_refused() -> None:
    with pytest.raises(FieldError):
        parse_shifts([])


def test_a_stop_takes_the_day_off_its_shift() -> None:
    reads = parse_stops([STOP_HEAD, "SH-00021,09:00,11:00,weather,squall"], DAYS)
    ident, stop = kept_stops(reads)[0]
    assert ident == "SH-00021"
    assert stop.began.date() == dt.date(2026, 3, 10)
    assert stop.reason is Reason.WEATHER
    assert stop.note == "squall"


def test_a_stop_against_a_shift_not_in_the_log_is_refused() -> None:
    reads = parse_stops([STOP_HEAD, "SH-00099,09:00,11:00,weather,"], DAYS)
    assert "not a shift in this log" in str(refused(reads)[0].trouble)


def test_a_reason_nobody_agreed_is_refused() -> None:
    reads = parse_stops([STOP_HEAD, "SH-00021,09:00,11:00,tea break,"], DAYS)
    assert "not a reason work stops" in str(refused(reads)[0].trouble)


def test_a_stop_that_ends_first_is_refused() -> None:
    reads = parse_stops([STOP_HEAD, "SH-00021,11:00,09:00,weather,"], DAYS)
    assert refused(reads)[0].line == 2


def test_a_bad_time_is_refused() -> None:
    reads = parse_stops([STOP_HEAD, "SH-00021,2500,11:00,weather,"], DAYS)
    assert "time of day" in str(refused(reads)[0].trouble)


def test_both_files_read_off_disk_together(tmp_path: Path) -> None:
    shifts = tmp_path / "shifts.csv"
    shifts.write_text("\n".join(GOOD_SHIFT) + "\n", encoding="utf-8")
    stops = tmp_path / "stops.csv"
    stops.write_text(STOP_HEAD + "\nSH-00021,09:00,11:00,weather,squall\n", encoding="utf-8")
    worked, stopped = parse_files(shifts, stops)
    assert len(kept_shifts(worked)) == 1
    assert len(kept_stops(stopped)) == 1


def test_the_stop_file_is_optional(tmp_path: Path) -> None:
    shifts = tmp_path / "shifts.csv"
    shifts.write_text("\n".join(GOOD_SHIFT) + "\n", encoding="utf-8")
    worked, stopped = parse_files(shifts)
    assert len(kept_shifts(worked)) == 1
    assert stopped == ()
