"""Reaches go into the book and come back out the same."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.errors import DuplicateError, MissingError
from scowbox.model.channel import Method, Reach, Template
from scowbox.store import reaches
from scowbox.store.book import book, counts
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline


@pytest.fixture
def open_book(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with book(tmp_path / "book.sqlite3", create=True) as connection:
        yield connection


def a_reach(
    ident: str = "RCH-012", begin: str = "100+00", end: str = "140+00", **over: object
) -> Reach:
    fields: dict[str, object] = {
        "ident": ident,
        "name": "Lower Range",
        "line": Reachline.parse(begin, end),
        "template": Template(
            bottom_width=400,
            authorized_depth=Depth.of_feet(42),
            side_slope=3,
            advance_maintenance=2,
            overdepth=2,
        ),
        "method": Method.SURVEY,
        "group": "base",
    }
    fields.update(over)
    return Reach(**fields)  # type: ignore[arg-type]


def test_a_reach_round_trips_through_the_book(open_book: sqlite3.Connection) -> None:
    written = a_reach()
    reaches.add(open_book, written)
    assert reaches.get(open_book, "RCH-012") == written


def test_a_reach_that_is_not_there_is_missing(open_book: sqlite3.Connection) -> None:
    with pytest.raises(MissingError):
        reaches.get(open_book, "RCH-999")


def test_the_same_identifier_twice_is_a_duplicate(open_book: sqlite3.Connection) -> None:
    reaches.add(open_book, a_reach())
    with pytest.raises(DuplicateError):
        reaches.add(open_book, a_reach(begin="200+00", end="240+00"))


def test_reaches_come_back_in_station_order(open_book: sqlite3.Connection) -> None:
    reaches.add(open_book, a_reach("RCH-014", "200+00", "240+00"))
    reaches.add(open_book, a_reach("RCH-012", "100+00", "140+00"))
    assert [r.ident for r in reaches.listed(open_book)] == ["RCH-012", "RCH-014"]


def test_a_group_holds_only_its_own(open_book: sqlite3.Connection) -> None:
    reaches.add(open_book, a_reach("RCH-012"))
    reaches.add(open_book, a_reach("RCH-014", "200+00", "240+00", group="entrance"))
    assert [r.ident for r in reaches.in_group(open_book, "entrance")] == ["RCH-014"]
    assert reaches.in_group(open_book, "nothing") == ()


def test_overlapping_finds_a_reach_that_shares_length(open_book: sqlite3.Connection) -> None:
    reaches.add(open_book, a_reach("RCH-012", "100+00", "140+00"))
    found = reaches.overlapping(open_book, Reachline.parse("120+00", "160+00"))
    assert [r.ident for r in found] == ["RCH-012"]


def test_adjoining_reaches_do_not_overlap(open_book: sqlite3.Connection) -> None:
    reaches.add(open_book, a_reach("RCH-012", "100+00", "140+00"))
    assert reaches.overlapping(open_book, Reachline.parse("140+00", "180+00")) == ()


def test_a_removed_reach_is_gone(open_book: sqlite3.Connection) -> None:
    reaches.add(open_book, a_reach())
    reaches.remove(open_book, "RCH-012")
    with pytest.raises(MissingError):
        reaches.get(open_book, "RCH-012")


def test_removing_what_is_not_there_says_so(open_book: sqlite3.Connection) -> None:
    with pytest.raises(MissingError):
        reaches.remove(open_book, "RCH-012")


def test_the_method_and_the_template_survive_the_round_trip(
    open_book: sqlite3.Connection,
) -> None:
    reaches.add(open_book, a_reach(method=Method.BOTH))
    back = reaches.get(open_book, "RCH-012")
    assert back.method is Method.BOTH
    assert back.template.pay_depth == Depth.of_feet(46)


def test_counts_reports_the_tables(open_book: sqlite3.Connection) -> None:
    reaches.add(open_book, a_reach())
    assert counts(open_book)["reach"] == 1


def test_a_book_that_is_not_there_is_not_created_by_accident(tmp_path: Path) -> None:
    with pytest.raises(MissingError), book(tmp_path / "nothing.sqlite3"):
        pass
