"""Sounding exports, and what a bad line does to the rest of the file."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from scowbox.errors import FieldError
from scowbox.feed.soundings import kept, parse_file, parse_lines, refused
from scowbox.units.clock import moment
from scowbox.units.depth import Depth
from scowbox.units.station import Station

DAY = dt.date(2025, 3, 14)
HEAD = "station,offset,depth,time"
GOOD = [HEAD, "100+00,-50.0,41.2,07:45", "100+00,0.0,43.8,07:45"]


def test_a_clean_file_reads_every_line() -> None:
    readings = parse_lines(GOOD, DAY)
    assert len(readings) == 2
    assert all(r.read for r in readings)


def test_the_fields_land_where_they_belong() -> None:
    shot = kept(parse_lines(GOOD, DAY))[0]
    assert shot.station == Station.parse("100+00")
    assert shot.offset == -50.0
    assert shot.raw_depth == Depth.of_feet(41.2)
    assert shot.taken == moment(DAY, "07:45")


def test_the_day_comes_from_the_caller_not_the_file() -> None:
    other = dt.date(2025, 4, 1)
    assert kept(parse_lines(GOOD, other))[0].taken.date() == other


def test_a_bad_line_does_not_stop_the_good_ones() -> None:
    readings = parse_lines([HEAD, "100+00,-50.0,41.2,07:45", "wrong,0,0,0"], DAY)
    assert len(kept(readings)) == 1
    assert len(refused(readings)) == 1


def test_a_refused_line_carries_its_line_number() -> None:
    readings = parse_lines([HEAD, "100+00,-50.0,41.2,07:45", "wrong,0,0,07:45"], DAY)
    bad = refused(readings)[0]
    assert bad.line == 3
    assert "stationing" in str(bad.trouble)


def test_a_short_row_says_how_many_fields_it_had() -> None:
    bad = refused(parse_lines([HEAD, "100+00,-50.0"], DAY))[0]
    assert "2 fields" in str(bad.trouble)


def test_a_field_that_is_not_a_number_is_named() -> None:
    bad = refused(parse_lines([HEAD, "100+00,left,41.2,07:45"], DAY))[0]
    assert "not both numbers" in str(bad.trouble)


def test_a_depth_of_zero_is_refused_by_the_record() -> None:
    bad = refused(parse_lines([HEAD, "100+00,0,0,07:45"], DAY))[0]
    assert "transducer" in str(bad.trouble)


def test_a_bad_time_is_refused() -> None:
    bad = refused(parse_lines([HEAD, "100+00,0,41.2,2545"], DAY))[0]
    assert "time of day" in str(bad.trouble)


def test_blank_lines_are_skipped() -> None:
    readings = parse_lines([HEAD, "", "100+00,0.0,41.2,07:45", ""], DAY)
    assert len(readings) == 1


def test_a_file_with_no_heading_is_refused() -> None:
    with pytest.raises(FieldError):
        parse_lines([], DAY)


def test_the_wrong_heading_is_refused_before_anything_is_read() -> None:
    with pytest.raises(FieldError) as caught:
        parse_lines(["x,y,z,t", "100+00,0.0,41.2,07:45"], DAY)
    assert "expected station,offset,depth,time" in str(caught.value)


def test_the_heading_is_read_case_insensitively() -> None:
    assert len(parse_lines(["Station,Offset,Depth,Time", "100+00,0,41.2,07:45"], DAY)) == 1


def test_a_file_on_disk_reads_the_same_way(tmp_path: Path) -> None:
    where = tmp_path / "shots.csv"
    where.write_text("\n".join(GOOD) + "\n", encoding="utf-8")
    assert len(kept(parse_file(where, DAY))) == 2
