"""Estimates are written once and read back whole."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.errors import DuplicateError, MissingError
from scowbox.model.contract import Contract, LineItem, Unit
from scowbox.pay.estimate import build
from scowbox.store import contracts, estimates
from scowbox.store.book import book
from scowbox.units.money import Money
from scowbox.units.volume import Yards

AWARD = dt.date(2025, 1, 20)
NTP = dt.date(2025, 2, 3)
THROUGH = dt.date(2025, 3, 31)
NUMBER = "W912PM-25-C-0014"

CONTRACT = Contract(
    number=NUMBER,
    awarded=AWARD,
    notice_to_proceed=NTP,
    days=180,
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


def an_estimate(number: int = 1, yards: float = 100000, previous: object = None):  # type: ignore[no-untyped-def]
    return build(
        CONTRACT,
        number,
        THROUGH,
        {"base": Yards.of_yards(yards)},
        {"LI-0009": 1.0},
        previous,  # type: ignore[arg-type]
    )


def test_an_estimate_round_trips_whole(open_book: sqlite3.Connection) -> None:
    estimates.add(open_book, an_estimate())
    assert estimates.get(open_book, "EST-001") == an_estimate()


def test_the_money_survives_the_round_trip(open_book: sqlite3.Connection) -> None:
    estimates.add(open_book, an_estimate())
    back = estimates.get(open_book, "EST-001")
    assert back.earned == an_estimate().earned
    assert back.due == an_estimate().due


def test_an_estimate_that_is_not_there_is_missing(open_book: sqlite3.Connection) -> None:
    with pytest.raises(MissingError):
        estimates.get(open_book, "EST-009")


def test_the_same_estimate_twice_is_a_duplicate(open_book: sqlite3.Connection) -> None:
    estimates.add(open_book, an_estimate())
    with pytest.raises(DuplicateError):
        estimates.add(open_book, an_estimate())


def test_an_estimate_on_a_contract_that_is_not_there_is_refused(
    open_book: sqlite3.Connection,
) -> None:
    stray = build(
        Contract("W912PM-25-C-0099", AWARD, NTP, 180, 0.05, Money.zero(), CONTRACT.items),
        1,
        THROUGH,
        {},
    )
    with pytest.raises(MissingError):
        estimates.add(open_book, stray)


def test_estimates_come_back_in_number_order(open_book: sqlite3.Connection) -> None:
    first = an_estimate(1)
    estimates.add(open_book, first)
    estimates.add(open_book, an_estimate(2, 160000, first))
    assert [e.number for e in estimates.listed(open_book, NUMBER)] == [1, 2]


def test_a_new_job_has_no_latest_estimate(open_book: sqlite3.Connection) -> None:
    assert estimates.latest(open_book, NUMBER) is None
    assert estimates.next_number(open_book, NUMBER) == 1


def test_the_latest_is_the_highest_numbered(open_book: sqlite3.Connection) -> None:
    first = an_estimate(1)
    estimates.add(open_book, first)
    estimates.add(open_book, an_estimate(2, 160000, first))
    last = estimates.latest(open_book, NUMBER)
    assert last is not None
    assert last.number == 2
    assert estimates.next_number(open_book, NUMBER) == 3


def test_the_lines_carry_their_previous_quantities(open_book: sqlite3.Connection) -> None:
    first = an_estimate(1)
    estimates.add(open_book, first)
    estimates.add(open_book, an_estimate(2, 160000, first))
    back = estimates.get(open_book, "EST-002")
    assert back.line("LI-0001").previous == 100000
    assert back.line("LI-0001").this_period == 60000


def test_another_contract_does_not_see_these_estimates(
    open_book: sqlite3.Connection,
) -> None:
    estimates.add(open_book, an_estimate())
    assert estimates.listed(open_book, "W912PM-25-C-0099") == ()
