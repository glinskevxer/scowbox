"""Reconciliations, one per reach, replaced only on purpose."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.errors import DuplicateError, MissingError
from scowbox.model.channel import Method, Reach, Template
from scowbox.model.reconciliation import Accepted, Reconciliation
from scowbox.store import reaches, reconciliations
from scowbox.store.book import book
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline
from scowbox.units.volume import Yards

DAY = dt.date(2025, 11, 4)


@pytest.fixture
def open_book(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with book(tmp_path / "book.sqlite3", create=True) as connection:
        for ident in ("RCH-012", "RCH-014"):
            reaches.add(
                connection,
                Reach(
                    ident=ident,
                    name="Lower Range",
                    line=Reachline.parse("100+00", "140+00"),
                    template=Template(
                        bottom_width=400, authorized_depth=Depth.of_feet(42), side_slope=3
                    ),
                    method=Method.BOTH,
                    group="base",
                ),
            )
        yield connection


def a_record(reach: str = "RCH-012", **over: object) -> Reconciliation:
    fields: dict[str, object] = {
        "reach": reach,
        "decided_on": DAY,
        "accepted": Accepted.SURVEY,
        "decided_by": "R. Beaufort",
        "note": "",
        "quantity": None,
    }
    fields.update(over)
    return Reconciliation(**fields)  # type: ignore[arg-type]


def test_a_reconciliation_round_trips(open_book: sqlite3.Connection) -> None:
    reconciliations.add(open_book, a_record())
    assert reconciliations.get(open_book, "RCH-012") == a_record()


def test_an_agreed_figure_survives_the_round_trip(open_book: sqlite3.Connection) -> None:
    agreed = a_record(
        accepted=Accepted.AGREED, quantity=Yards.of_yards(24000), note="split the difference"
    )
    reconciliations.add(open_book, agreed)
    assert reconciliations.get(open_book, "RCH-012").quantity == Yards.of_yards(24000)


def test_a_reach_can_only_be_settled_once(open_book: sqlite3.Connection) -> None:
    reconciliations.add(open_book, a_record())
    with pytest.raises(DuplicateError):
        reconciliations.add(open_book, a_record(accepted=Accepted.SCOW))


def test_replacing_is_a_separate_act(open_book: sqlite3.Connection) -> None:
    reconciliations.add(open_book, a_record())
    reconciliations.replace(open_book, a_record(accepted=Accepted.SCOW))
    assert reconciliations.get(open_book, "RCH-012").accepted is Accepted.SCOW


def test_replacing_what_is_not_there_says_so(open_book: sqlite3.Connection) -> None:
    with pytest.raises(MissingError):
        reconciliations.replace(open_book, a_record())


def test_a_reconciliation_for_a_reach_that_is_not_there_is_refused(
    open_book: sqlite3.Connection,
) -> None:
    with pytest.raises(MissingError):
        reconciliations.add(open_book, a_record("RCH-999"))


def test_find_comes_back_empty_rather_than_raising(open_book: sqlite3.Connection) -> None:
    assert reconciliations.find(open_book, "RCH-012") is None
    reconciliations.add(open_book, a_record())
    assert reconciliations.find(open_book, "RCH-012") is not None


def test_get_raises_where_find_does_not(open_book: sqlite3.Connection) -> None:
    with pytest.raises(MissingError):
        reconciliations.get(open_book, "RCH-012")


def test_reconciliations_come_back_oldest_first(open_book: sqlite3.Connection) -> None:
    reconciliations.add(open_book, a_record("RCH-014", decided_on=dt.date(2025, 12, 1)))
    reconciliations.add(open_book, a_record("RCH-012"))
    assert [r.reach for r in reconciliations.listed(open_book)] == ["RCH-012", "RCH-014"]


def test_a_removed_reconciliation_is_gone(open_book: sqlite3.Connection) -> None:
    reconciliations.add(open_book, a_record())
    reconciliations.remove(open_book, "RCH-012")
    assert reconciliations.listed(open_book) == ()


def test_removing_what_is_not_there_says_so(open_book: sqlite3.Connection) -> None:
    with pytest.raises(MissingError):
        reconciliations.remove(open_book, "RCH-012")
