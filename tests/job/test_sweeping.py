"""Running the sweep over everything in the book."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.job.sweeping import gather
from scowbox.model.channel import Method, Reach, Template
from scowbox.model.placement import Ground, PlacementArea
from scowbox.model.plant import Dredge, Plant
from scowbox.model.scow import Scow, ScowTrip
from scowbox.model.shift import Shift
from scowbox.model.window import Restriction, Window
from scowbox.store import placements, reaches, scows, shifts, trips, windows
from scowbox.store.book import book
from scowbox.units.clock import moment
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline

DAY = dt.date(2026, 5, 6)


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


def test_an_empty_book_sweeps_clean(open_book: sqlite3.Connection) -> None:
    found = gather(open_book)
    assert found.clean
    assert (found.shifts, found.trips, found.tickets) == (0, 0, 0)


def test_the_records_are_counted(open_book: sqlite3.Connection) -> None:
    shifts.add(
        open_book,
        Shift("SH-00021", "DR-003", "RCH-012", moment(DAY, "06:00"), moment(DAY, "18:00")),
    )
    trips.add(open_book, ScowTrip("TR-04188", "SC-004", "RCH-012", DAY, "PA-002"))
    found = gather(open_book)
    assert found.shifts == 1
    assert found.trips == 1


def test_a_trip_with_no_ticket_is_a_warning(open_book: sqlite3.Connection) -> None:
    trips.add(open_book, ScowTrip("TR-04188", "SC-004", "RCH-012", DAY, "PA-002"))
    assert not gather(open_book).clean


def test_a_closed_month_turns_it_into_a_violation(open_book: sqlite3.Connection) -> None:
    trips.add(open_book, ScowTrip("TR-04188", "SC-004", "RCH-012", DAY, "PA-002"))
    found = gather(open_book, dt.date(2026, 5, 31))
    assert found.findings[0].severity.reportable


def test_a_shift_inside_a_closure_is_swept_up(open_book: sqlite3.Connection) -> None:
    windows.add(
        open_book,
        Window(
            "loggerhead", dt.date(2026, 5, 1), dt.date(2026, 11, 30), Restriction.CLOSED, "NMFS"
        ),
    )
    shifts.add(
        open_book,
        Shift("SH-00021", "DR-003", "RCH-012", moment(DAY, "06:00"), moment(DAY, "18:00")),
    )
    found = gather(open_book)
    assert any(f.kind == "window" for f in found.findings)
