"""Gathering production out of the book."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.job.rates import average_load, daily, for_reach
from scowbox.model.channel import Method, Reach, Template
from scowbox.model.placement import Ground, PlacementArea
from scowbox.model.plant import Dredge, Plant
from scowbox.model.scow import BoxReading, Corner, Scow, ScowTrip
from scowbox.model.shift import Shift
from scowbox.store import placements, reaches, scows, shifts, trips
from scowbox.store.book import book
from scowbox.units.clock import moment
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline
from scowbox.units.volume import Yards

DAY = dt.date(2025, 12, 1)
NEXT = dt.date(2025, 12, 2)


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


def a_trip(connection: sqlite3.Connection, ident: str, day: dt.date, loaded: float | None) -> None:
    readings = () if loaded is None else tuple(BoxReading(c, 12.0, loaded) for c in Corner)
    trips.add(connection, ScowTrip(ident, "SC-004", "RCH-012", day, "PA-002", readings))


def a_shift(connection: sqlite3.Connection, ident: str, day: dt.date, end: str) -> None:
    shifts.add(
        connection,
        Shift(ident, "DR-003", "RCH-012", moment(day, "06:00"), moment(day, end)),
    )


def test_no_trips_is_no_average_load(open_book: sqlite3.Connection) -> None:
    assert average_load(open_book) == Yards.zero()


def test_the_average_load_is_over_the_measured_trips(open_book: sqlite3.Connection) -> None:
    a_trip(open_book, "TR-00001", DAY, 4.0)
    a_trip(open_book, "TR-00002", DAY, 6.0)
    assert average_load(open_book).yards == pytest.approx(1960.0, abs=0.01)


def test_an_unmeasured_trip_does_not_drag_the_average_down(
    open_book: sqlite3.Connection,
) -> None:
    a_trip(open_book, "TR-00001", DAY, 4.0)
    a_trip(open_book, "TR-00002", DAY, None)
    assert average_load(open_book).yards == pytest.approx(2240.0, abs=0.01)


def test_a_reach_rate_counts_every_trip_out_of_it(open_book: sqlite3.Connection) -> None:
    a_shift(open_book, "SH-00021", DAY, "18:00")
    a_trip(open_book, "TR-00001", DAY, 4.0)
    a_trip(open_book, "TR-00002", DAY, 4.0)
    rate = for_reach(open_book, "RCH-012", Yards.of_yards(4480))
    assert rate.hours == 12.0
    assert rate.trips == 2
    assert rate.yards_per_hour == pytest.approx(373.3, abs=0.1)


def test_the_daily_rates_price_trips_at_the_average_load(
    open_book: sqlite3.Connection,
) -> None:
    a_shift(open_book, "SH-00021", DAY, "18:00")
    a_trip(open_book, "TR-00001", DAY, 4.0)
    a_trip(open_book, "TR-00002", NEXT, 4.0)
    rates = dict(daily(open_book))
    assert rates[DAY].yards == Yards.of_yards(2240)
    assert rates[NEXT].hours == 0.0


def test_the_daily_rates_can_be_narrowed_to_a_reach(
    open_book: sqlite3.Connection,
) -> None:
    a_shift(open_book, "SH-00021", DAY, "18:00")
    a_trip(open_book, "TR-00001", DAY, 4.0)
    assert len(daily(open_book, "RCH-012")) == 1
    assert daily(open_book, "RCH-999") == ()


def test_an_empty_book_has_no_daily_rates(open_book: sqlite3.Connection) -> None:
    assert daily(open_book) == ()
