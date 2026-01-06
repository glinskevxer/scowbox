"""The contract the estimates see is the modified one."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.job.contract import as_modified, current
from scowbox.model.contract import Contract, LineItem, Unit
from scowbox.model.modification import Change, Modification
from scowbox.store import contracts, modifications
from scowbox.store.book import book
from scowbox.units.money import Money

NUMBER = "W912PM-25-C-0014"


@pytest.fixture
def open_book(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with book(tmp_path / "book.sqlite3", create=True) as connection:
        contracts.add(
            connection,
            Contract(
                number=NUMBER,
                awarded=dt.date(2025, 1, 20),
                notice_to_proceed=dt.date(2025, 2, 3),
                days=365,
                retainage=0.05,
                liquidated=Money.parse("$3,400.00"),
                items=(
                    LineItem("LI-0001", "Dredging", Unit.CUBIC_YARD, Money.parse("$7.35"), "base"),
                ),
            ),
        )
        yield connection


def test_an_unmodified_contract_comes_back_as_it_is(
    open_book: sqlite3.Connection,
) -> None:
    found = as_modified(open_book)
    assert found.count == 0
    assert found.contract.days == 365


def test_a_time_extension_reaches_the_contract(open_book: sqlite3.Connection) -> None:
    modifications.add(
        open_book,
        NUMBER,
        Modification("P00003", dt.date(2026, 1, 12), Change.TIME, "Window", days=45),
    )
    assert current(open_book).days == 410


def test_a_price_change_reaches_the_schedule(open_book: sqlite3.Connection) -> None:
    modifications.add(
        open_book,
        NUMBER,
        Modification(
            "P00004",
            dt.date(2026, 1, 12),
            Change.PRICE,
            "Rock",
            item="LI-0001",
            price=Money.parse("$9.10"),
        ),
    )
    assert current(open_book).item("LI-0001").unit_price == Money.parse("$9.10")


def test_the_contract_can_be_named_where_there_are_two(
    open_book: sqlite3.Connection,
) -> None:
    assert current(open_book, NUMBER).number == NUMBER
