"""Modifications in the book, keyed on the contract and the number."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.errors import DuplicateError, MissingError
from scowbox.model.contract import Contract, LineItem, Unit
from scowbox.model.modification import Change, Modification
from scowbox.store import contracts, modifications
from scowbox.store.book import book
from scowbox.units.money import Money

NUMBER = "W912PM-25-C-0014"
DAY = dt.date(2026, 1, 12)


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


def a_time(number: str = "P00003", day: dt.date = DAY) -> Modification:
    return Modification(number, day, Change.TIME, "Time extension", days=45)


def a_price(number: str = "P00004") -> Modification:
    return Modification(
        number, DAY, Change.PRICE, "Rock", item="LI-0001", price=Money.parse("$9.10")
    )


def test_a_time_extension_round_trips(open_book: sqlite3.Connection) -> None:
    modifications.add(open_book, NUMBER, a_time())
    assert modifications.get(open_book, NUMBER, "P00003") == a_time()


def test_a_price_change_keeps_its_money(open_book: sqlite3.Connection) -> None:
    modifications.add(open_book, NUMBER, a_price())
    back = modifications.get(open_book, NUMBER, "P00004")
    assert back.price == Money.parse("$9.10")
    assert back.item == "LI-0001"


def test_the_same_number_twice_is_a_duplicate(open_book: sqlite3.Connection) -> None:
    modifications.add(open_book, NUMBER, a_time())
    with pytest.raises(DuplicateError):
        modifications.add(open_book, NUMBER, a_time())


def test_a_modification_on_a_contract_that_is_not_there_is_refused(
    open_book: sqlite3.Connection,
) -> None:
    with pytest.raises(MissingError):
        modifications.add(open_book, "W912PM-25-C-0099", a_time())


def test_one_that_is_not_there_is_missing(open_book: sqlite3.Connection) -> None:
    with pytest.raises(MissingError):
        modifications.get(open_book, NUMBER, "P00099")


def test_they_come_back_oldest_first(open_book: sqlite3.Connection) -> None:
    modifications.add(open_book, NUMBER, a_time("P00005", dt.date(2026, 3, 1)))
    modifications.add(open_book, NUMBER, a_time("P00003"))
    assert [m.number for m in modifications.listed(open_book, NUMBER)] == [
        "P00003",
        "P00005",
    ]


def test_another_contract_sees_none_of_them(open_book: sqlite3.Connection) -> None:
    modifications.add(open_book, NUMBER, a_time())
    assert modifications.listed(open_book, "W912PM-25-C-0099") == ()


def test_a_removed_modification_is_gone(open_book: sqlite3.Connection) -> None:
    modifications.add(open_book, NUMBER, a_time())
    modifications.remove(open_book, NUMBER, "P00003")
    assert modifications.listed(open_book, NUMBER) == ()


def test_removing_one_that_is_not_there_says_so(open_book: sqlite3.Connection) -> None:
    with pytest.raises(MissingError):
        modifications.remove(open_book, NUMBER, "P00003")
