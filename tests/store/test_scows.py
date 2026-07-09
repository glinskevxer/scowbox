"""Scows and placement areas go into the book and come back the same."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.errors import DuplicateError, MissingError, StateError
from scowbox.model.placement import Ground, PlacementArea
from scowbox.model.scow import Scow
from scowbox.store import placements, scows
from scowbox.store.book import book
from scowbox.units.volume import Yards


@pytest.fixture
def open_book(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with book(tmp_path / "book.sqlite3", create=True) as connection:
        yield connection


def a_scow(ident: str = "SC-004") -> Scow:
    return Scow(ident, "Dixie 41", inside_length=180, inside_width=42, inside_depth=14)


def an_ocean(ident: str = "PA-002") -> PlacementArea:
    return PlacementArea(ident, "Wilmington ODMDS", Ground.OCEAN, "SAW-2019-01142")


def a_cell(ident: str = "PA-004") -> PlacementArea:
    return PlacementArea(
        ident, "Eagle Island cell 3", Ground.UPLAND, "SAW-2019-01143", Yards.of_yards(500000)
    )


def test_a_scow_round_trips(open_book: sqlite3.Connection) -> None:
    scows.add(open_book, a_scow())
    assert scows.get(open_book, "SC-004") == a_scow()


def test_a_scow_that_is_not_there_is_missing(open_book: sqlite3.Connection) -> None:
    with pytest.raises(MissingError):
        scows.get(open_book, "SC-009")


def test_the_same_scow_twice_is_a_duplicate(open_book: sqlite3.Connection) -> None:
    scows.add(open_book, a_scow())
    with pytest.raises(DuplicateError):
        scows.add(open_book, a_scow())


def test_scows_come_back_by_identifier(open_book: sqlite3.Connection) -> None:
    scows.add(open_book, a_scow("SC-009"))
    scows.add(open_book, a_scow("SC-004"))
    assert [s.ident for s in scows.listed(open_book)] == ["SC-004", "SC-009"]


def test_a_removed_scow_is_gone(open_book: sqlite3.Connection) -> None:
    scows.add(open_book, a_scow())
    scows.remove(open_book, "SC-004")
    assert scows.listed(open_book) == ()


def test_removing_a_scow_that_is_not_there_says_so(open_book: sqlite3.Connection) -> None:
    with pytest.raises(MissingError):
        scows.remove(open_book, "SC-004")


def test_an_open_site_keeps_its_missing_capacity(open_book: sqlite3.Connection) -> None:
    placements.add(open_book, an_ocean())
    assert placements.get(open_book, "PA-002").capacity is None


def test_a_cell_keeps_its_capacity_to_the_hundredth(open_book: sqlite3.Connection) -> None:
    placements.add(open_book, a_cell())
    assert placements.get(open_book, "PA-004").capacity == Yards.of_yards(500000)


def test_areas_can_be_asked_for_by_ground(open_book: sqlite3.Connection) -> None:
    placements.add(open_book, an_ocean())
    placements.add(open_book, a_cell())
    found = placements.of_ground(open_book, Ground.UPLAND)
    assert [a.ident for a in found] == ["PA-004"]
    assert placements.of_ground(open_book, Ground.BEACH) == ()


def test_the_same_area_twice_is_a_duplicate(open_book: sqlite3.Connection) -> None:
    placements.add(open_book, an_ocean())
    with pytest.raises(DuplicateError):
        placements.add(open_book, an_ocean())


def test_an_area_that_is_not_there_is_missing(open_book: sqlite3.Connection) -> None:
    with pytest.raises(MissingError):
        placements.get(open_book, "PA-009")


def test_areas_are_listed_by_identifier(open_book: sqlite3.Connection) -> None:
    placements.add(open_book, a_cell())
    placements.add(open_book, an_ocean())
    assert [a.ident for a in placements.listed(open_book)] == ["PA-002", "PA-004"]


def test_a_removed_area_is_gone(open_book: sqlite3.Connection) -> None:
    placements.add(open_book, an_ocean())
    placements.remove(open_book, "PA-002")
    assert placements.listed(open_book) == ()


def test_removing_an_area_that_is_not_there_says_so(open_book: sqlite3.Connection) -> None:
    with pytest.raises(MissingError):
        placements.remove(open_book, "PA-002")


def test_an_area_with_tickets_against_it_cannot_be_removed(
    open_book: sqlite3.Connection,
) -> None:
    from scowbox.model.channel import Method, Reach, Template
    from scowbox.model.scow import ScowTrip
    from scowbox.store import reaches, trips
    from scowbox.units.depth import Depth
    from scowbox.units.station import Reachline

    placements.add(open_book, an_ocean())
    scows.add(open_book, a_scow())
    reaches.add(
        open_book,
        Reach(
            ident="RCH-012",
            name="Lower Range",
            line=Reachline.parse("100+00", "140+00"),
            template=Template(bottom_width=400, authorized_depth=Depth.of_feet(42), side_slope=3),
            method=Method.SCOW,
            group="base",
        ),
    )
    trips.add(
        open_book,
        ScowTrip("TR-04188", "SC-004", "RCH-012", dt.date(2026, 7, 6), "PA-002"),
    )
    with pytest.raises(StateError):
        placements.remove(open_book, "PA-002")
    with pytest.raises(StateError):
        reaches.remove(open_book, "RCH-012")
