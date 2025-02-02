"""Tide interpolation, and the two things it refuses to do."""

from __future__ import annotations

import datetime as dt

import pytest

from scowbox.datum.tide import TideReading, TideRecord
from scowbox.errors import FieldError, MissingError, RuleError
from scowbox.units.clock import moment

DAY = dt.date(2025, 3, 14)


def a_record(*pairs: tuple[str, float], gauge: str = "8658120") -> TideRecord:
    return TideRecord(gauge, tuple(TideReading(moment(DAY, c), h) for c, h in pairs))


def test_a_reading_on_the_gauge_comes_straight_back() -> None:
    record = a_record(("07:00", 1.0), ("07:06", 1.6))
    assert record.height_at(moment(DAY, "07:06")) == 1.6


def test_a_moment_between_readings_interpolates_straight() -> None:
    record = a_record(("07:00", 1.0), ("07:06", 1.6))
    assert record.height_at(moment(DAY, "07:03")) == 1.3


def test_interpolation_walks_the_whole_record() -> None:
    record = a_record(("07:00", 1.0), ("07:06", 1.6), ("07:12", 1.0))
    assert record.height_at(moment(DAY, "07:09")) == 1.3


def test_the_ends_of_the_record_are_covered() -> None:
    record = a_record(("07:00", 1.0), ("07:06", 1.6))
    assert record.covers(moment(DAY, "07:00"))
    assert record.covers(moment(DAY, "07:06"))
    assert not record.covers(moment(DAY, "06:59"))


def test_a_moment_before_the_gauge_started_is_missing_not_guessed() -> None:
    record = a_record(("07:00", 1.0), ("07:06", 1.6))
    with pytest.raises(MissingError):
        record.height_at(moment(DAY, "06:54"))


def test_a_moment_after_the_gauge_stopped_is_missing_not_guessed() -> None:
    record = a_record(("07:00", 1.0), ("07:06", 1.6))
    with pytest.raises(MissingError):
        record.height_at(moment(DAY, "07:12"))


def test_a_wide_gap_is_refused_rather_than_bridged() -> None:
    record = a_record(("07:00", 1.0), ("09:00", 3.0))
    with pytest.raises(RuleError) as caught:
        record.height_at(moment(DAY, "08:00"))
    assert "120 minute gap" in str(caught.value)


def test_a_gap_inside_the_allowance_still_interpolates() -> None:
    record = a_record(("07:00", 1.0), ("07:30", 2.0))
    assert record.height_at(moment(DAY, "07:15")) == 1.5


def test_gaps_reports_every_stretch_that_cannot_be_bridged() -> None:
    record = a_record(("07:00", 1.0), ("07:06", 1.2), ("09:00", 3.0), ("09:06", 3.1))
    assert record.gaps() == ((moment(DAY, "07:06"), moment(DAY, "09:00")),)


def test_a_record_with_no_readings_is_refused() -> None:
    with pytest.raises(FieldError):
        TideRecord("8658120", ())


def test_a_record_out_of_time_order_is_refused() -> None:
    with pytest.raises(FieldError):
        a_record(("07:06", 1.6), ("07:00", 1.0))


def test_a_repeated_reading_time_is_refused() -> None:
    with pytest.raises(FieldError):
        a_record(("07:00", 1.0), ("07:00", 1.2))


def test_a_record_names_its_gauge() -> None:
    with pytest.raises(FieldError):
        a_record(("07:00", 1.0), gauge=" ")


def test_a_reading_off_this_coast_is_refused() -> None:
    with pytest.raises(FieldError):
        TideReading(moment(DAY, "07:00"), 40.0)
