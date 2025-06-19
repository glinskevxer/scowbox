"""Windows in the book, and asking the book what governs a day."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.errors import DuplicateError, MissingError
from scowbox.model.window import Restriction, Window
from scowbox.store import windows
from scowbox.store.book import book


@pytest.fixture
def open_book(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with book(tmp_path / "book.sqlite3", create=True) as connection:
        yield connection


def a_window(
    name: str = "loggerhead",
    begins: dt.date = dt.date(2025, 5, 1),
    ends: dt.date = dt.date(2025, 11, 30),
    restriction: Restriction = Restriction.CLOSED,
    reach: str = "",
) -> Window:
    return Window(name, begins, ends, restriction, "NMFS", reach)


def test_a_window_round_trips(open_book: sqlite3.Connection) -> None:
    windows.add(open_book, a_window())
    assert windows.listed(open_book) == (a_window(),)


def test_the_same_window_twice_is_a_duplicate(open_book: sqlite3.Connection) -> None:
    windows.add(open_book, a_window())
    with pytest.raises(DuplicateError):
        windows.add(open_book, a_window())


def test_the_same_closure_in_two_seasons_sits_side_by_side(
    open_book: sqlite3.Connection,
) -> None:
    windows.add(open_book, a_window())
    windows.add(
        open_book,
        a_window(begins=dt.date(2026, 5, 1), ends=dt.date(2026, 11, 30)),
    )
    assert len(windows.listed(open_book)) == 2


def test_the_same_window_on_two_reaches_sits_side_by_side(
    open_book: sqlite3.Connection,
) -> None:
    windows.add(open_book, a_window(reach="RCH-012"))
    windows.add(open_book, a_window(reach="RCH-014"))
    assert len(windows.listed(open_book)) == 2


def test_windows_come_back_in_date_order(open_book: sqlite3.Connection) -> None:
    windows.add(open_book, a_window())
    windows.add(open_book, a_window("sturgeon", dt.date(2025, 2, 1), dt.date(2025, 4, 30)))
    assert [w.name for w in windows.listed(open_book)] == ["sturgeon", "loggerhead"]


def test_the_book_builds_a_schedule_that_answers(open_book: sqlite3.Connection) -> None:
    windows.add(open_book, a_window())
    schedule = windows.schedule(open_book)
    assert schedule.closed(dt.date(2025, 7, 1), "RCH-012")
    assert not schedule.closed(dt.date(2025, 4, 1), "RCH-012")


def test_covering_asks_the_book_for_one_day(open_book: sqlite3.Connection) -> None:
    windows.add(open_book, a_window("oyster", restriction=Restriction.OBSERVER))
    windows.add(open_book, a_window())
    found = windows.covering(open_book, dt.date(2025, 7, 1), "RCH-012")
    assert [w.name for w in found] == ["loggerhead", "oyster"]


def test_covering_leaves_out_another_reach(open_book: sqlite3.Connection) -> None:
    windows.add(open_book, a_window(reach="RCH-014"))
    assert windows.covering(open_book, dt.date(2025, 7, 1), "RCH-012") == ()


def test_covering_leaves_out_another_day(open_book: sqlite3.Connection) -> None:
    windows.add(open_book, a_window())
    assert windows.covering(open_book, dt.date(2025, 4, 1), "RCH-012") == ()


def test_a_removed_window_is_gone(open_book: sqlite3.Connection) -> None:
    windows.add(open_book, a_window())
    windows.remove(open_book, "loggerhead", "", dt.date(2025, 5, 1))
    assert windows.listed(open_book) == ()


def test_removing_a_window_that_is_not_there_says_so(open_book: sqlite3.Connection) -> None:
    with pytest.raises(MissingError):
        windows.remove(open_book, "loggerhead", "", dt.date(2025, 5, 1))
