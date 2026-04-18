"""The estimate sheet and the history behind it."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.model.contract import Contract, LineItem, Unit
from scowbox.pay.estimate import build
from scowbox.report.estimate import history, item_history, render
from scowbox.store import contracts, estimates
from scowbox.store.book import book
from scowbox.units.money import Money
from scowbox.units.volume import Yards

NUMBER = "W912PM-25-C-0014"
FIRST = dt.date(2026, 3, 31)
SECOND = dt.date(2026, 4, 30)

CONTRACT = Contract(
    number=NUMBER,
    awarded=dt.date(2025, 1, 20),
    notice_to_proceed=dt.date(2025, 2, 3),
    days=730,
    retainage=0.05,
    liquidated=Money.parse("$3,400.00"),
    items=(
        LineItem("LI-0001", "Dredging, base", Unit.CUBIC_YARD, Money.parse("$7.35"), "base"),
        LineItem("LI-0009", "Mobilisation", Unit.LUMP_SUM, Money.parse("$1,250,000.00")),
    ),
)


@pytest.fixture
def open_book(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with book(tmp_path / "book.sqlite3", create=True) as connection:
        contracts.add(connection, CONTRACT)
        yield connection


def two_estimates(connection: sqlite3.Connection) -> None:
    first = build(CONTRACT, 1, FIRST, {"base": Yards.of_yards(100000)}, {"LI-0009": 1.0})
    estimates.add(connection, first)
    estimates.add(
        connection,
        build(CONTRACT, 2, SECOND, {"base": Yards.of_yards(160000)}, {"LI-0009": 1.0}, first),
    )


def test_an_estimate_names_the_one_before_it(open_book: sqlite3.Connection) -> None:
    two_estimates(open_book)
    out = "\n".join(render(open_book, "EST-002"))
    assert "previous      EST-001" in out


def test_the_first_estimate_has_none_before_it(open_book: sqlite3.Connection) -> None:
    two_estimates(open_book)
    assert "previous      none" in "\n".join(render(open_book, "EST-001"))


def test_the_line_shows_what_moved(open_book: sqlite3.Connection) -> None:
    two_estimates(open_book)
    out = "\n".join(render(open_book, "EST-002"))
    assert "100,000.00" in out
    assert "160,000.00" in out
    assert "$441,000.00" in out


def test_a_line_that_did_not_move_earns_nothing_this_period(
    open_book: sqlite3.Connection,
) -> None:
    two_estimates(open_book)
    out = "\n".join(render(open_book, "EST-002"))
    assert "LI-0009" in out
    assert "$0.00" in out


def test_the_money_is_laid_out_under_the_lines(open_book: sqlite3.Connection) -> None:
    two_estimates(open_book)
    out = "\n".join(render(open_book, "EST-002"))
    assert "earned" in out
    assert "paid before" in out
    assert "due" in out


def test_a_final_estimate_says_what_it_released(open_book: sqlite3.Connection) -> None:
    estimates.add(
        open_book, build(CONTRACT, 1, FIRST, {"base": Yards.of_yards(100000)}, final=True)
    )
    out = "\n".join(render(open_book, "EST-001"))
    assert "final         yes" in out
    assert "released" in out


def test_an_empty_history_says_so(open_book: sqlite3.Connection) -> None:
    assert "No estimate written yet." in "\n".join(history(open_book))


def test_the_history_lists_every_estimate(open_book: sqlite3.Connection) -> None:
    two_estimates(open_book)
    out = "\n".join(history(open_book))
    assert "EST-001" in out
    assert "EST-002" in out
    assert "paid to date" in out


def test_an_item_is_followed_across_the_estimates(open_book: sqlite3.Connection) -> None:
    two_estimates(open_book)
    out = "\n".join(item_history(open_book, "LI-0001"))
    assert "Line item LI-0001" in out
    assert out.count("EST-00") == 2


def test_an_item_on_no_estimate_says_so(open_book: sqlite3.Connection) -> None:
    two_estimates(open_book)
    assert "is on no estimate" in "\n".join(item_history(open_book, "LI-0099"))
