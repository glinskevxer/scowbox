"""The closeout report reads as a list somebody works through."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.boxmeasure.bulking import Bulking
from scowbox.report.closeout import render
from scowbox.store import placements, reaches, scows
from scowbox.store.book import book
from tests.report.bookmaking import a_reach as make_reach
from tests.report.bookmaking import a_scow as make_scow
from tests.report.bookmaking import a_trip, an_area

DAY = dt.date(2026, 5, 6)
SILT = Bulking("silt", 1.20)


@pytest.fixture
def open_book(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with book(tmp_path / "book.sqlite3", create=True) as connection:
        yield connection


def a_reach(connection: sqlite3.Connection) -> None:
    reaches.add(connection, make_reach())


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
    scows.add(open_book, make_scow())
    placements.add(open_book, an_area())
    a_trip(open_book, "TR-04188", DAY, loaded=None)
    out = text(open_book)
    assert "Trips with no placement ticket: 1" in out
    assert "TR-04188" in out


def test_the_warnings_and_violations_are_counted(open_book: sqlite3.Connection) -> None:
    out = text(open_book)
    assert "violations    0" in out
    assert "warnings      0" in out
