"""Trips, their box readings and the tickets that close them out."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.errors import DuplicateError, MissingError
from scowbox.model.channel import Method, Reach, Template
from scowbox.model.placement import Grade, Ground, PlacementArea, PlacementTicket
from scowbox.model.scow import BoxReading, Corner, Scow, ScowTrip
from scowbox.store import placements, reaches, scows, trips
from scowbox.store.book import book
from scowbox.units.clock import moment
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline
from scowbox.units.volume import Yards

DAY = dt.date(2025, 4, 2)


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
        yield connection


def four_readings() -> tuple[BoxReading, ...]:
    return tuple(BoxReading(corner, 12.0, 4.0) for corner in Corner)


def a_trip(ident: str = "TR-04188", day: dt.date = DAY, **over: object) -> ScowTrip:
    fields: dict[str, object] = {
        "ident": ident,
        "scow": "SC-004",
        "reach": "RCH-012",
        "loaded_on": day,
        "placement": "PA-002",
        "readings": (),
    }
    fields.update(over)
    return ScowTrip(**fields)  # type: ignore[arg-type]


def a_ticket(trip: str = "TR-04188") -> PlacementTicket:
    return PlacementTicket(
        trip, "PA-002", moment(DAY, "11:20"), Yards.of_yards(1800), Grade.SUITABLE
    )


def test_a_trip_round_trips(open_book: sqlite3.Connection) -> None:
    trips.add(open_book, a_trip())
    assert trips.get(open_book, "TR-04188") == a_trip()


def test_readings_written_with_the_trip_come_back(open_book: sqlite3.Connection) -> None:
    trips.add(open_book, a_trip(readings=four_readings()))
    back = trips.get(open_book, "TR-04188")
    assert back.measured
    assert {r.corner for r in back.readings} == set(Corner)


def test_measuring_replaces_the_readings(open_book: sqlite3.Connection) -> None:
    trips.add(open_book, a_trip(readings=four_readings()))
    deeper = tuple(BoxReading(corner, 12.0, 2.0) for corner in Corner)
    trips.measure(open_book, "TR-04188", deeper)
    back = trips.get(open_book, "TR-04188")
    assert len(back.readings) == 4
    assert back.readings[0].material == 10.0


def test_measuring_a_trip_that_is_not_there_says_so(open_book: sqlite3.Connection) -> None:
    with pytest.raises(MissingError):
        trips.measure(open_book, "TR-09999", four_readings())


def test_a_trip_from_a_scow_that_is_not_there_is_refused(
    open_book: sqlite3.Connection,
) -> None:
    with pytest.raises(MissingError):
        trips.add(open_book, a_trip(scow="SC-999"))


def test_the_same_trip_twice_is_a_duplicate(open_book: sqlite3.Connection) -> None:
    trips.add(open_book, a_trip())
    with pytest.raises(DuplicateError):
        trips.add(open_book, a_trip())


def test_trips_of_a_reach_come_back_oldest_first(open_book: sqlite3.Connection) -> None:
    trips.add(open_book, a_trip("TR-04190", dt.date(2025, 4, 5)))
    trips.add(open_book, a_trip("TR-04188"))
    assert [t.ident for t in trips.for_reach(open_book, "RCH-012")] == [
        "TR-04188",
        "TR-04190",
    ]


def test_every_trip_in_the_book_is_listed(open_book: sqlite3.Connection) -> None:
    trips.add(open_book, a_trip("TR-04190", dt.date(2025, 4, 5)))
    trips.add(open_book, a_trip("TR-04188"))
    assert [t.ident for t in trips.listed(open_book)] == ["TR-04188", "TR-04190"]


def test_a_period_takes_both_its_ends(open_book: sqlite3.Connection) -> None:
    trips.add(open_book, a_trip("TR-04188", dt.date(2025, 4, 2)))
    trips.add(open_book, a_trip("TR-04190", dt.date(2025, 4, 5)))
    trips.add(open_book, a_trip("TR-04192", dt.date(2025, 4, 9)))
    found = trips.between(open_book, dt.date(2025, 4, 2), dt.date(2025, 4, 5))
    assert [t.ident for t in found] == ["TR-04188", "TR-04190"]


def test_a_ticket_closes_a_trip_out(open_book: sqlite3.Connection) -> None:
    trips.add(open_book, a_trip())
    trips.release(open_book, a_ticket())
    assert trips.ticket_of(open_book, "TR-04188").yards == Yards.of_yards(1800)


def test_a_trip_without_a_ticket_is_listed(open_book: sqlite3.Connection) -> None:
    trips.add(open_book, a_trip("TR-04188"))
    trips.add(open_book, a_trip("TR-04190", dt.date(2025, 4, 5)))
    trips.release(open_book, a_ticket("TR-04188"))
    assert trips.untick(open_book) == ("TR-04190",)


def test_two_tickets_for_one_trip_are_refused(open_book: sqlite3.Connection) -> None:
    trips.add(open_book, a_trip())
    trips.release(open_book, a_ticket())
    with pytest.raises(DuplicateError):
        trips.release(open_book, a_ticket())


def test_a_ticket_for_a_trip_that_is_not_there_says_so(
    open_book: sqlite3.Connection,
) -> None:
    with pytest.raises(MissingError):
        trips.release(open_book, a_ticket("TR-09999"))


def test_a_trip_with_no_ticket_has_none_to_fetch(open_book: sqlite3.Connection) -> None:
    trips.add(open_book, a_trip())
    with pytest.raises(MissingError):
        trips.ticket_of(open_book, "TR-04188")


def test_tickets_for_an_area_come_back_oldest_first(open_book: sqlite3.Connection) -> None:
    trips.add(open_book, a_trip("TR-04188"))
    trips.release(open_book, a_ticket("TR-04188"))
    assert [t.trip for t in trips.tickets_for_area(open_book, "PA-002")] == ["TR-04188"]
    assert trips.tickets_for_area(open_book, "PA-009") == ()


def test_a_run_of_trips_carries_its_readings(open_book: sqlite3.Connection) -> None:
    trips.add(open_book, a_trip("TR-04188", readings=four_readings()))
    trips.add(open_book, a_trip("TR-04190", dt.date(2025, 4, 5)))
    found = {t.ident: t for t in trips.listed(open_book)}
    assert found["TR-04188"].measured
    assert not found["TR-04190"].measured


def test_a_run_is_one_query_for_the_readings(open_book: sqlite3.Connection) -> None:
    for number in range(20):
        trips.add(
            open_book,
            a_trip(f"TR-{number + 1:05d}", dt.date(2025, 4, 2), readings=four_readings()),
        )
    statements: list[str] = []
    open_book.set_trace_callback(statements.append)
    try:
        found = trips.listed(open_book)
    finally:
        open_book.set_trace_callback(None)
    assert len(found) == 20
    assert all(trip.measured for trip in found)
    assert len(statements) <= 3, statements
