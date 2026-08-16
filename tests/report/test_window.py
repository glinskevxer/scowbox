"""The window report counts the days a planner can actually work."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.errors import FieldError
from scowbox.model.window import Restriction, Window
from scowbox.report.window import render
from scowbox.store import reaches, windows
from scowbox.store.book import book
from tests.report.bookmaking import a_reach

FIRST = dt.date(2026, 6, 1)
LAST = dt.date(2026, 6, 30)


@pytest.fixture
def open_book(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with book(tmp_path / "book.sqlite3", create=True) as connection:
        reaches.add(connection, a_reach())
        yield connection


def a_window(
    name: str = "loggerhead",
    begins: dt.date = dt.date(2026, 6, 1),
    ends: dt.date = dt.date(2026, 6, 10),
    restriction: Restriction = Restriction.CLOSED,
    reach: str = "",
) -> Window:
    return Window(name, begins, ends, restriction, "NMFS", reach)


def text(connection: sqlite3.Connection) -> str:
    return "\n".join(render(connection, FIRST, LAST))


def test_a_period_with_no_window_is_all_open(open_book: sqlite3.Connection) -> None:
    out = text(open_book)
    assert "days          30" in out
    assert "No window touches this period." in out


def test_a_closure_takes_days_off_the_workable_count(
    open_book: sqlite3.Connection,
) -> None:
    windows.add(open_book, a_window())
    out = text(open_book)
    assert "RCH-012" in out
    assert "20" in out


def test_an_observer_window_is_still_workable(open_book: sqlite3.Connection) -> None:
    windows.add(open_book, a_window(restriction=Restriction.OBSERVER))
    out = text(open_book)
    assert "1 windows touch this period" in out
    assert "observer required" in out


def test_the_next_open_day_is_named(open_book: sqlite3.Connection) -> None:
    windows.add(open_book, a_window())
    assert "2026-06-11" in text(open_book)


def test_a_window_outside_the_period_is_left_out(open_book: sqlite3.Connection) -> None:
    windows.add(open_book, a_window(begins=dt.date(2026, 9, 1), ends=dt.date(2026, 9, 30)))
    assert "No window touches this period." in text(open_book)


def test_a_window_on_another_reach_does_not_close_this_one(
    open_book: sqlite3.Connection,
) -> None:
    windows.add(open_book, a_window(reach="RCH-014"))
    out = text(open_book)
    assert "1 windows touch this period" in out
    assert "RCH-014" in out


def test_a_book_with_no_reach_says_so(tmp_path: Path) -> None:
    with book(tmp_path / "bare.sqlite3", create=True) as connection:
        assert "No reach in this book." in "\n".join(render(connection, FIRST, LAST))


def test_a_period_that_runs_backwards_is_refused(
    open_book: sqlite3.Connection,
) -> None:
    with pytest.raises(FieldError):
        render(open_book, LAST, FIRST)
