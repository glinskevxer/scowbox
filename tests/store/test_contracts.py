"""The contract comes back whole or not at all."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.errors import DuplicateError, MissingError
from scowbox.model.contract import Contract, LineItem, Unit
from scowbox.store import contracts
from scowbox.store.book import book
from scowbox.units.money import Money

AWARD = dt.date(2025, 1, 20)
NTP = dt.date(2025, 2, 3)


@pytest.fixture
def open_book(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with book(tmp_path / "book.sqlite3", create=True) as connection:
        yield connection


def a_contract(number: str = "W912PM-25-C-0014") -> Contract:
    return Contract(
        number=number,
        awarded=AWARD,
        notice_to_proceed=NTP,
        days=180,
        retainage=0.05,
        liquidated=Money.parse("$3,400.00"),
        items=(
            LineItem(
                "LI-0001", "Dredging, base", Unit.CUBIC_YARD, Money.parse("$7.35"), "base", 480000
            ),
            LineItem("LI-0009", "Mobilisation", Unit.LUMP_SUM, Money.parse("$1,250,000.00")),
        ),
    )


def test_a_contract_round_trips_whole(open_book: sqlite3.Connection) -> None:
    contracts.add(open_book, a_contract())
    assert contracts.get(open_book, "W912PM-25-C-0014") == a_contract()


def test_the_prices_survive_as_whole_cents(open_book: sqlite3.Connection) -> None:
    contracts.add(open_book, a_contract())
    back = contracts.get(open_book, "W912PM-25-C-0014")
    assert back.item("LI-0009").unit_price == Money.parse("$1,250,000.00")


def test_the_bid_quantity_survives(open_book: sqlite3.Connection) -> None:
    contracts.add(open_book, a_contract())
    assert contracts.get(open_book, "W912PM-25-C-0014").item("LI-0001").estimated == 480000


def test_a_contract_that_is_not_there_is_missing(open_book: sqlite3.Connection) -> None:
    with pytest.raises(MissingError):
        contracts.get(open_book, "W912PM-25-C-0099")


def test_the_same_contract_twice_is_a_duplicate(open_book: sqlite3.Connection) -> None:
    contracts.add(open_book, a_contract())
    with pytest.raises(DuplicateError):
        contracts.add(open_book, a_contract())


def test_two_contracts_may_use_the_same_line_item_numbers(
    open_book: sqlite3.Connection,
) -> None:
    contracts.add(open_book, a_contract("W912PM-25-C-0014"))
    contracts.add(open_book, a_contract("W912PM-25-C-0020"))
    first = contracts.get(open_book, "W912PM-25-C-0014")
    second = contracts.get(open_book, "W912PM-25-C-0020")
    assert first.item("LI-0001") == second.item("LI-0001")
    assert len(first.items) == 2


def test_the_numbers_come_back_in_order(open_book: sqlite3.Connection) -> None:
    contracts.add(open_book, a_contract("W912PM-25-C-0020"))
    contracts.add(open_book, a_contract("W912PM-25-C-0014"))
    assert contracts.numbers(open_book) == (
        "W912PM-25-C-0014",
        "W912PM-25-C-0020",
    )


def test_one_contract_can_be_asked_for_without_naming_it(
    open_book: sqlite3.Connection,
) -> None:
    contracts.add(open_book, a_contract())
    assert contracts.only(open_book).number == "W912PM-25-C-0014"


def test_an_empty_book_has_no_contract_to_take(open_book: sqlite3.Connection) -> None:
    with pytest.raises(MissingError):
        contracts.only(open_book)


def test_two_contracts_cannot_be_taken_without_naming_one(
    open_book: sqlite3.Connection,
) -> None:
    contracts.add(open_book, a_contract("W912PM-25-C-0014"))
    contracts.add(open_book, a_contract("W912PM-25-C-0020"))
    with pytest.raises(MissingError, match="the book holds 2"):
        contracts.only(open_book)
