"""Gauge readings, fetched by window with a margin at each end."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.datum.tide import TideReading
from scowbox.errors import MissingError
from scowbox.store import tides
from scowbox.store.book import book
from scowbox.units.clock import moment

DAY = dt.date(2025, 3, 14)


@pytest.fixture
def open_book(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with book(tmp_path / "book.sqlite3", create=True) as connection:
        yield connection


def some_readings(*pairs: tuple[str, float]) -> list[TideReading]:
    return [TideReading(moment(DAY, clock), height) for clock, height in pairs]


def test_readings_round_trip(open_book: sqlite3.Connection) -> None:
    tides.add_readings(open_book, "8658120", some_readings(("07:00", 1.0), ("07:06", 1.6)))
    record = tides.record_for(open_book, "8658120", moment(DAY, "07:00"), moment(DAY, "07:06"))
    assert record.height_at(moment(DAY, "07:03")) == 1.3


def test_writing_the_same_reading_twice_keeps_one(open_book: sqlite3.Connection) -> None:
    tides.add_readings(open_book, "8658120", some_readings(("07:00", 1.0)))
    tides.add_readings(open_book, "8658120", some_readings(("07:00", 1.0), ("07:06", 1.6)))
    record = tides.record_for(open_book, "8658120", moment(DAY, "07:00"), moment(DAY, "07:06"))
    assert len(record.readings) == 2


def test_the_window_reaches_one_interval_past_each_end(open_book: sqlite3.Connection) -> None:
    tides.add_readings(
        open_book,
        "8658120",
        some_readings(("06:54", 0.8), ("07:00", 1.0), ("07:06", 1.6), ("07:12", 1.8)),
    )
    record = tides.record_for(open_book, "8658120", moment(DAY, "07:00"), moment(DAY, "07:06"))
    assert record.begins == moment(DAY, "06:54")
    assert record.ends == moment(DAY, "07:12")


def test_readings_well_outside_the_window_stay_out(open_book: sqlite3.Connection) -> None:
    tides.add_readings(
        open_book, "8658120", some_readings(("06:00", 0.2), ("07:00", 1.0), ("07:06", 1.6))
    )
    record = tides.record_for(open_book, "8658120", moment(DAY, "07:00"), moment(DAY, "07:06"))
    assert record.begins == moment(DAY, "07:00")


def test_another_gauge_is_not_mixed_in(open_book: sqlite3.Connection) -> None:
    tides.add_readings(open_book, "8658120", some_readings(("07:00", 1.0), ("07:06", 1.6)))
    tides.add_readings(open_book, "8658163", some_readings(("07:00", 4.0), ("07:06", 4.6)))
    record = tides.record_for(open_book, "8658163", moment(DAY, "07:00"), moment(DAY, "07:06"))
    assert record.height_at(moment(DAY, "07:00")) == 4.0


def test_a_gauge_with_nothing_in_the_window_is_missing(open_book: sqlite3.Connection) -> None:
    tides.add_readings(open_book, "8658120", some_readings(("07:00", 1.0)))
    with pytest.raises(MissingError):
        tides.record_for(open_book, "8658120", moment(DAY, "12:00"), moment(DAY, "13:00"))


def test_gauges_lists_what_the_book_holds(open_book: sqlite3.Connection) -> None:
    tides.add_readings(open_book, "8658163", some_readings(("07:00", 4.0)))
    tides.add_readings(open_book, "8658120", some_readings(("07:00", 1.0)))
    assert tides.gauges(open_book) == ("8658120", "8658163")


def test_span_reports_the_first_and_last_reading(open_book: sqlite3.Connection) -> None:
    tides.add_readings(
        open_book, "8658120", some_readings(("07:00", 1.0), ("09:00", 2.0), ("08:00", 1.5))
    )
    first, last = tides.span(open_book, "8658120")
    assert first == moment(DAY, "07:00")
    assert last == moment(DAY, "09:00")


def test_the_span_of_a_gauge_with_nothing_is_missing(open_book: sqlite3.Connection) -> None:
    with pytest.raises(MissingError):
        tides.span(open_book, "8658120")
