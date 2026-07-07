"""The fleet report, dredges by hours and scows by loads."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.model.scow import BoxReading, Corner, ScowTrip
from scowbox.model.shift import Downtime, Reason, Shift
from scowbox.report.fleet import render
from scowbox.store import placements, reaches, scows, shifts, trips
from scowbox.store.book import book
from scowbox.units.clock import moment
from tests.report.bookmaking import a_dredge as make_dredge
from tests.report.bookmaking import a_reach, an_area
from tests.report.bookmaking import a_scow as make_scow

DAY = dt.date(2026, 4, 22)


@pytest.fixture
def open_book(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with book(tmp_path / "book.sqlite3", create=True) as connection:
        reaches.add(connection, a_reach())
        placements.add(connection, an_area())
        yield connection


def a_dredge(connection: sqlite3.Connection) -> None:
    shifts.add_dredge(connection, make_dredge())


def a_scow(connection: sqlite3.Connection) -> None:
    scows.add(connection, make_scow())


def text(connection: sqlite3.Connection) -> str:
    return "\n".join(render(connection))


def test_an_empty_book_says_it_has_no_plant(open_book: sqlite3.Connection) -> None:
    out = text(open_book)
    assert "No dredge on this job." in out
    assert "No scow on this job." in out


def test_a_dredge_with_no_shifts_shows_no_share(open_book: sqlite3.Connection) -> None:
    a_dredge(open_book)
    out = text(open_book)
    assert "DR-003" in out
    assert "Cherokee" in out


def test_a_dredge_reports_its_hours_and_its_share(open_book: sqlite3.Connection) -> None:
    a_dredge(open_book)
    shifts.add(
        open_book,
        Shift(
            "SH-00021",
            "DR-003",
            "RCH-012",
            moment(DAY, "06:00"),
            moment(DAY, "18:00"),
            (Downtime(moment(DAY, "09:00"), moment(DAY, "12:00"), Reason.WEATHER),),
        ),
    )
    out = text(open_book)
    assert "12.0" in out
    assert "75%" in out


def test_a_scow_with_no_trips_carries_nothing(open_book: sqlite3.Connection) -> None:
    a_scow(open_book)
    out = text(open_book)
    assert "SC-004" in out
    assert "0 cy" in out


def test_a_scow_reports_its_loads_and_how_full_they_were(
    open_book: sqlite3.Connection,
) -> None:
    a_scow(open_book)
    trips.add(
        open_book,
        ScowTrip(
            "TR-04188",
            "SC-004",
            "RCH-012",
            DAY,
            "PA-002",
            tuple(BoxReading(c, 12.0, 4.0) for c in Corner),
        ),
    )
    out = text(open_book)
    assert "2,240 cy" in out
    assert "57%" in out


def test_an_unmeasured_trip_counts_as_a_trip_and_not_as_a_box(
    open_book: sqlite3.Connection,
) -> None:
    a_scow(open_book)
    trips.add(open_book, ScowTrip("TR-04190", "SC-004", "RCH-012", DAY, "PA-002"))
    out = text(open_book)
    assert "trips         1" in out
    assert "carried       0 cy" in out
