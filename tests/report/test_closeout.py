"""The closeout report reads as a list somebody works through."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.boxmeasure.bulking import Bulking
from scowbox.model.channel import Method, Reach, Template
from scowbox.model.placement import Ground, PlacementArea
from scowbox.model.scow import Scow, ScowTrip
from scowbox.report.closeout import render
from scowbox.store import placements, reaches, scows, trips
from scowbox.store.book import book
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline

DAY = dt.date(2026, 5, 6)
SILT = Bulking("silt", 1.20)


@pytest.fixture
def open_book(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with book(tmp_path / "book.sqlite3", create=True) as connection:
        yield connection


def a_reach(connection: sqlite3.Connection) -> None:
    reaches.add(
        connection,
        Reach(
            ident="RCH-012",
            name="Lower Range",
            line=Reachline.parse("100+00", "140+00"),
            template=Template(bottom_width=400, authorized_depth=Depth.of_feet(42), side_slope=3),
            method=Method.SCOW,
            group="base",
        ),
    )


def text(connection: sqlite3.Connection) -> str:
    return "\n".join(render(connection, SILT))


def test_an_empty_book_can_be_closed(open_book: sqlite3.Connection) -> None:
    out = text(open_book)
    assert "outstanding   0" in out
    assert "Nothing outstanding." in out


def test_every_section_says_none_when_it_is_empty(open_book: sqlite3.Connection) -> None:
    out = text(open_book)
    assert "Reaches nobody can measure: none" in out
    assert "Trips with no placement ticket: none" in out
    assert "Reaches in dispute: none" in out


def test_an_unmeasured_reach_is_listed_with_its_reason(
    open_book: sqlite3.Connection,
) -> None:
    a_reach(open_book)
    out = text(open_book)
    assert "Reaches nobody can measure: 1" in out
    assert "RCH-012" in out


def test_the_verdict_counts_what_is_in_the_way(open_book: sqlite3.Connection) -> None:
    a_reach(open_book)
    assert "1 things stand in the way of a final estimate." in text(open_book)


def test_a_trip_with_no_ticket_is_listed(open_book: sqlite3.Connection) -> None:
    a_reach(open_book)
    scows.add(open_book, Scow("SC-004", "Dixie 41", 180, 42, 14))
    placements.add(
        open_book,
        PlacementArea("PA-002", "Wilmington ODMDS", Ground.OCEAN, "SAW-2019-01142"),
    )
    trips.add(open_book, ScowTrip("TR-04188", "SC-004", "RCH-012", DAY, "PA-002"))
    out = text(open_book)
    assert "Trips with no placement ticket: 1" in out
    assert "TR-04188" in out


def test_the_warnings_and_violations_are_counted(open_book: sqlite3.Connection) -> None:
    out = text(open_book)
    assert "violations    0" in out
    assert "warnings      0" in out
