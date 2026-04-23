"""Trip sheets, and the five readings that come together or not at all."""

from __future__ import annotations

from pathlib import Path

import pytest

from scowbox.errors import FieldError
from scowbox.feed.trips import kept, parse_file, parse_lines, refused

HEAD = "trip,scow,reach,day,placement,light,pb,sb,ps,ss"
MEASURED = "TR-00001,SC-004,RCH-012,2026-05-04,PA-002,12.0,4.0,4.0,4.0,4.0"
PLAIN = "TR-00002,SC-004,RCH-012,2026-05-04,PA-002,,,,,"


def test_a_measured_row_carries_its_box() -> None:
    trip = kept(parse_lines([HEAD, MEASURED]))[0]
    assert trip.ident == "TR-00001"
    assert trip.measured
    assert trip.readings[0].material == 8.0


def test_an_unmeasured_row_reads_as_a_trip() -> None:
    trip = kept(parse_lines([HEAD, PLAIN]))[0]
    assert not trip.measured
    assert trip.placement == "PA-002"


def test_both_shapes_read_in_one_sheet() -> None:
    reads = parse_lines([HEAD, MEASURED, PLAIN])
    assert len(kept(reads)) == 2
    assert refused(reads) == ()


def test_three_readings_out_of_five_are_refused() -> None:
    partial = "TR-00003,SC-004,RCH-012,2026-05-04,PA-002,12.0,4.0,4.0,,"
    bad = refused(parse_lines([HEAD, partial]))[0]
    assert "all five readings or none" in str(bad.trouble)
    assert bad.line == 2


def test_a_loaded_reading_deeper_than_light_is_refused() -> None:
    upside = "TR-00003,SC-004,RCH-012,2026-05-04,PA-002,4.0,12.0,12.0,12.0,12.0"
    bad = refused(parse_lines([HEAD, upside]))[0]
    assert "further down than light" in str(bad.trouble)


def test_a_reading_that_is_not_a_number_is_refused() -> None:
    wordy = "TR-00003,SC-004,RCH-012,2026-05-04,PA-002,twelve,4.0,4.0,4.0,4.0"
    bad = refused(parse_lines([HEAD, wordy]))[0]
    assert "a number of feet" in str(bad.trouble)


def test_a_day_that_is_not_a_day_is_refused() -> None:
    bad = refused(parse_lines([HEAD, "TR-00003,SC-004,RCH-012,Monday,PA-002,,,,,"]))[0]
    assert "not a day" in str(bad.trouble)


def test_a_bad_identifier_is_refused() -> None:
    bad = refused(parse_lines([HEAD, "TR-3,SC-004,RCH-012,2026-05-04,PA-002,,,,,"]))[0]
    assert "trip identifier" in str(bad.trouble)


def test_a_short_row_says_how_many_fields_it_had() -> None:
    bad = refused(parse_lines([HEAD, "TR-00003,SC-004"]))[0]
    assert "2 fields" in str(bad.trouble)


def test_the_wrong_heading_is_refused_before_anything_is_read() -> None:
    with pytest.raises(FieldError):
        parse_lines(["a,b,c", "1,2,3"])


def test_an_empty_sheet_is_refused() -> None:
    with pytest.raises(FieldError):
        parse_lines([])


def test_blank_rows_are_skipped() -> None:
    assert len(parse_lines([HEAD, "", MEASURED, ""])) == 1


def test_a_sheet_on_disk_reads_the_same_way(tmp_path: Path) -> None:
    where = tmp_path / "trips.csv"
    where.write_text(HEAD + "\n" + MEASURED + "\n", encoding="utf-8")
    assert len(kept(parse_file(where))) == 1
