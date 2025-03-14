"""Gauge downloads: what is kept, what is counted and what is left out."""

from __future__ import annotations

from pathlib import Path

import pytest

from scowbox.errors import FieldError
from scowbox.feed.tides import SITE_OFFSET, parse_file, parse_lines
from scowbox.units.clock import SITE_ZONE

HEAD = "Date Time,Water Level,Sigma,O,F,R,L,Quality"
GOOD = [
    HEAD,
    "2025-03-14 07:00,1.023,0.010,0,0,0,0,v",
    "2025-03-14 07:06,1.610,0.010,0,0,0,0,v",
]


def test_the_offset_stapled_on_is_the_project_zone() -> None:
    assert SITE_OFFSET == "-0500"
    assert parse_lines(GOOD, "8658120").readings[0].at.tzinfo == SITE_ZONE


def test_a_clean_download_reads_every_row() -> None:
    download = parse_lines(GOOD, "8658120")
    assert download.count == 2
    assert download.gauge == "8658120"


def test_the_height_and_the_time_land_where_they_belong() -> None:
    reading = parse_lines(GOOD, "8658120").readings[0]
    assert reading.height == 1.023
    assert reading.at.hour == 7
    assert reading.at.utcoffset() is not None


def test_a_verified_download_says_so() -> None:
    assert parse_lines(GOOD, "8658120").all_verified


def test_preliminary_readings_are_kept_and_counted() -> None:
    download = parse_lines([*GOOD, "2025-03-14 07:12,1.700,0.010,0,0,0,0,p"], "8658120")
    assert download.count == 3
    assert download.preliminary == 1
    assert not download.all_verified


def test_a_flat_flagged_reading_is_left_out() -> None:
    download = parse_lines([*GOOD, "2025-03-14 07:12,1.700,0.010,0,1,0,0,v"], "8658120")
    assert download.count == 2
    assert download.flagged == 1


def test_a_row_that_will_not_read_is_reported_by_line() -> None:
    download = parse_lines([*GOOD, "not a time,1.700,0.010,0,0,0,0,v"], "8658120")
    assert download.refused == (4,)
    assert download.count == 2


def test_a_height_off_this_coast_is_refused() -> None:
    download = parse_lines([*GOOD, "2025-03-14 07:12,40.0,0.010,0,0,0,0,v"], "8658120")
    assert download.refused == (4,)


def test_blank_rows_are_skipped() -> None:
    assert parse_lines([HEAD, "", GOOD[1], ""], "8658120").count == 1


def test_a_narrow_download_still_reads() -> None:
    download = parse_lines(["Date Time,Water Level", "2025-03-14 07:00,1.023"], "8658120")
    assert download.count == 1
    assert download.all_verified


def test_an_empty_download_is_refused() -> None:
    with pytest.raises(FieldError):
        parse_lines([], "8658120")


def test_a_download_without_a_level_column_is_refused() -> None:
    with pytest.raises(FieldError) as caught:
        parse_lines(["Date Time,Sigma", "2025-03-14 07:00,0.01"], "8658120")
    assert "water level" in str(caught.value)


def test_a_download_without_a_time_column_is_refused() -> None:
    with pytest.raises(FieldError):
        parse_lines(["Water Level,Sigma", "1.023,0.01"], "8658120")


def test_a_file_on_disk_reads_the_same_way(tmp_path: Path) -> None:
    where = tmp_path / "gauge.csv"
    where.write_text("\n".join(GOOD) + "\n", encoding="utf-8")
    assert parse_file(where, "8658120").count == 2
