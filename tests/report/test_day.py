"""The day report, over a book with a day's work in it."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.errors import StateError
from scowbox.model.channel import Method, Reach, Template
from scowbox.model.placement import Grade, Ground, PlacementArea, PlacementTicket
from scowbox.model.plant import Dredge, Plant
from scowbox.model.scow import BoxReading, Corner, Scow, ScowTrip
from scowbox.model.shift import Downtime, Reason, Shift
from scowbox.model.window import Restriction, Window
from scowbox.report.day import _box, render
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


def test_a_suspect_box_measure_says_what_is_wrong_with_it(
    open_book: sqlite3.Connection,
) -> None:
    wedge = (
        BoxReading(Corner.PORT_BOW, 12.0, 1.0),
        BoxReading(Corner.STARBOARD_BOW, 12.0, 1.0),
        BoxReading(Corner.PORT_STERN, 12.0, 7.0),
        BoxReading(Corner.STARBOARD_STERN, 12.0, 7.0),
    )
    trips.add(open_book, ScowTrip("TR-04188", "SC-004", "RCH-012", DAY, "PA-002", wedge))
    out = text(open_book)
    assert "trim +6.00 ft" in out


def test_a_day_that_placed_nothing_says_so(open_book: sqlite3.Connection) -> None:
    assert "Nothing placed on this day." in text(open_book)


def test_a_book_with_no_placement_area_says_so(tmp_path: Path) -> None:
    with book(tmp_path / "bare.sqlite3", create=True) as connection:
        assert "No placement area in this book." in "\n".join(render(connection, DAY))


def test_the_day_s_loads_are_summed_against_the_area(
    open_book: sqlite3.Connection,
) -> None:
    a_trip(open_book)
    trips.release(
        open_book,
        PlacementTicket(
            "TR-04188", "PA-002", moment(DAY, "11:20"), Yards.of_yards(1800), Grade.SUITABLE
        ),
    )
    out = text(open_book)
    assert "PA-002        1 loads today, 1,800.00 cy placed, open" in out


def test_a_load_placed_on_another_day_is_not_counted(
    open_book: sqlite3.Connection,
) -> None:
    a_trip(open_book)
    trips.release(
        open_book,
        PlacementTicket(
            "TR-04188",
            "PA-002",
            moment(dt.date(2025, 8, 7), "11:20"),
            Yards.of_yards(1800),
            Grade.SUITABLE,
        ),
    )
    assert "Nothing placed on this day." in text(open_book)


def test_a_trip_in_a_scow_that_has_gone_does_not_take_the_page_down() -> None:
    trip = ScowTrip(
        "TR-04188",
        "SC-004",
        "RCH-012",
        DAY,
        "PA-002",
        tuple(BoxReading(c, 12.0, 4.0) for c in Corner),
    )
    assert _box({}, trip) == ("-", "scow struck off")


def test_a_scow_with_trips_against_it_cannot_be_struck_off(
    open_book: sqlite3.Connection,
) -> None:
    a_trip(open_book)
    with pytest.raises(StateError, match="still has records against it"):
        scows.remove(open_book, "SC-004")


def test_a_box_measured_from_the_wrong_reference_does_not_either(
    open_book: sqlite3.Connection,
) -> None:
    deep = tuple(BoxReading(c, 16.0, 4.0) for c in Corner)
    trips.add(open_book, ScowTrip("TR-04190", "SC-004", "RCH-012", DAY, "PA-002", deep))
    out = text(open_book)
    assert "TR-04190" in out
    assert "box unusable" in out


def test_another_day_does_not_appear(open_book: sqlite3.Connection) -> None:
    a_shift(open_book)
    a_trip(open_book)
    out = text(open_book, dt.date(2025, 8, 7))
    assert "No shift logged." in out
    assert "No scow trip logged." in out
