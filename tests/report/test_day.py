"""The day report, over a book with a day's work in it."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.model.channel import Method, Reach, Template
from scowbox.model.placement import Grade, Ground, PlacementArea, PlacementTicket
from scowbox.model.plant import Dredge, Plant
from scowbox.model.scow import BoxReading, Corner, Scow, ScowTrip
from scowbox.model.shift import Downtime, Reason, Shift
from scowbox.model.window import Restriction, Window
from scowbox.report.day import render
from scowbox.store import placements, reaches, scows, shifts, trips, windows
from scowbox.store.book import book
from scowbox.units.clock import moment
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline
from scowbox.units.volume import Yards

DAY = dt.date(2025, 8, 6)


@pytest.fixture
def open_book(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with book(tmp_path / "book.sqlite3", create=True) as connection:
        reaches.add(
            connection,
            Reach(
                ident="RCH-012",
                name="Lower Range",
                line=Reachline.parse("100+00", "140+00"),
                template=Template(
                    bottom_width=400, authorized_depth=Depth.of_feet(42), side_slope=3
                ),
                method=Method.SCOW,
                group="base",
            ),
        )
        scows.add(connection, Scow("SC-004", "Dixie 41", 180, 42, 14))
        placements.add(
            connection,
            PlacementArea("PA-002", "Wilmington ODMDS", Ground.OCEAN, "SAW-2019-01142"),
        )
        shifts.add_dredge(
            connection, Dredge("DR-003", "Cherokee", Plant.MECHANICAL, "Norfolk Dredging")
        )
        yield connection


def a_shift(connection: sqlite3.Connection, *stops: Downtime) -> None:
    shifts.add(
        connection,
        Shift(
            ident="SH-00021",
            dredge="DR-003",
            reach="RCH-012",
            began=moment(DAY, "06:00"),
            ended=moment(DAY, "18:00"),
            downtimes=stops,
        ),
    )


def a_trip(connection: sqlite3.Connection, *, measured: bool = True) -> None:
    readings = tuple(BoxReading(c, 12.0, 4.0) for c in Corner) if measured else ()
    trips.add(
        connection,
        ScowTrip("TR-04188", "SC-004", "RCH-012", DAY, "PA-002", readings),
    )


def text(connection: sqlite3.Connection, day: dt.date = DAY) -> str:
    return "\n".join(render(connection, day))


def test_an_empty_day_says_so(open_book: sqlite3.Connection) -> None:
    out = text(open_book)
    assert "No shift logged." in out
    assert "No scow trip logged." in out
    assert "Nothing outstanding." in out


def test_the_report_is_headed_with_the_day(open_book: sqlite3.Connection) -> None:
    assert text(open_book).startswith("Day report 2025-08-06")


def test_a_shift_shows_its_hours(open_book: sqlite3.Connection) -> None:
    a_shift(open_book)
    out = text(open_book)
    assert "SH-00021" in out
    assert "effective     12.00 of 12.00 hours" in out


def test_downtime_is_split_on_the_day_report(open_book: sqlite3.Connection) -> None:
    a_shift(
        open_book,
        Downtime(moment(DAY, "09:00"), moment(DAY, "11:00"), Reason.WEATHER),
        Downtime(moment(DAY, "13:00"), moment(DAY, "14:00"), Reason.BREAKDOWN),
    )
    out = text(open_book)
    assert "allowable     2.00 hours" in out
    assert "contractor    1.00 hours" in out


def test_a_measured_trip_shows_its_yards(open_book: sqlite3.Connection) -> None:
    a_trip(open_book)
    out = text(open_book)
    assert "TR-04188" in out
    assert "2,240 cy" in out
    assert "measured" in out


def test_an_unmeasured_trip_says_so(open_book: sqlite3.Connection) -> None:
    a_trip(open_book, measured=False)
    assert "unmeasured" in text(open_book)


def test_a_trip_without_a_ticket_is_reported_twice(open_book: sqlite3.Connection) -> None:
    a_trip(open_book)
    out = text(open_book)
    assert "no ticket" in out
    assert "no placement ticket" in out


def test_a_ticketed_trip_shows_where_it_went(open_book: sqlite3.Connection) -> None:
    a_trip(open_book)
    trips.release(
        open_book,
        PlacementTicket(
            "TR-04188", "PA-002", moment(DAY, "11:20"), Yards.of_yards(1800), Grade.SUITABLE
        ),
    )
    out = text(open_book)
    assert "PA-002" in out
    assert "Nothing outstanding." in out


def test_working_inside_a_closure_is_reported(open_book: sqlite3.Connection) -> None:
    windows.add(
        open_book,
        Window(
            "loggerhead", dt.date(2025, 5, 1), dt.date(2025, 11, 30), Restriction.CLOSED, "NMFS"
        ),
    )
    a_shift(open_book)
    out = text(open_book)
    assert "1 violations" in out
    assert "loggerhead" in out


def test_another_day_does_not_appear(open_book: sqlite3.Connection) -> None:
    a_shift(open_book)
    a_trip(open_book)
    out = text(open_book, dt.date(2025, 8, 7))
    assert "No shift logged." in out
    assert "No scow trip logged." in out
