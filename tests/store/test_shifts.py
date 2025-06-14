"""Dredges, shifts and interruptions in the book."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.errors import DuplicateError, MissingError
from scowbox.model.channel import Method, Reach, Template
from scowbox.model.plant import Dredge, Plant
from scowbox.model.shift import Downtime, Reason, Shift
from scowbox.store import reaches, shifts
from scowbox.store.book import book
from scowbox.units.clock import moment
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline

DAY = dt.date(2025, 6, 4)
NEXT = dt.date(2025, 6, 5)


@pytest.fixture
def open_book(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with book(tmp_path / "book.sqlite3", create=True) as connection:
        reaches.add(
            connection,
            Reach(
                ident="RCH-012",
                name="Lower Range",
                line=Reachline.parse("100+00", "140+00"),
                template=Template(
                    bottom_width=400, authorized_depth=Depth.of_feet(42), side_slope=3
                ),
                method=Method.SCOW,
                group="base",
            ),
        )
        shifts.add_dredge(
            connection, Dredge("DR-003", "Cherokee", Plant.MECHANICAL, "Norfolk Dredging")
        )
        yield connection


def a_shift(ident: str = "SH-00021", day: dt.date = DAY, *stops: Downtime) -> Shift:
    return Shift(
        ident=ident,
        dredge="DR-003",
        reach="RCH-012",
        began=moment(day, "06:00"),
        ended=moment(day, "18:00"),
        downtimes=stops,
    )


def a_stop(day: dt.date = DAY, reason: Reason = Reason.WEATHER) -> Downtime:
    return Downtime(moment(day, "09:00"), moment(day, "11:00"), reason, "squall")


def test_a_dredge_round_trips(open_book: sqlite3.Connection) -> None:
    assert shifts.dredge(open_book, "DR-003").plant is Plant.MECHANICAL


def test_the_same_dredge_twice_is_a_duplicate(open_book: sqlite3.Connection) -> None:
    with pytest.raises(DuplicateError):
        shifts.add_dredge(open_book, Dredge("DR-003", "Cherokee", Plant.CUTTER, "Norfolk Dredging"))


def test_a_dredge_that_is_not_there_is_missing(open_book: sqlite3.Connection) -> None:
    with pytest.raises(MissingError):
        shifts.dredge(open_book, "DR-009")


def test_dredges_are_listed_by_identifier(open_book: sqlite3.Connection) -> None:
    shifts.add_dredge(open_book, Dredge("DR-001", "Currituck", Plant.HOPPER, "USACE"))
    assert [d.ident for d in shifts.dredges(open_book)] == ["DR-001", "DR-003"]


def test_a_shift_round_trips(open_book: sqlite3.Connection) -> None:
    shifts.add(open_book, a_shift())
    assert shifts.get(open_book, "SH-00021") == a_shift()


def test_interruptions_written_with_the_shift_come_back(
    open_book: sqlite3.Connection,
) -> None:
    shifts.add(open_book, a_shift("SH-00021", DAY, a_stop()))
    back = shifts.get(open_book, "SH-00021")
    assert back.down_minutes == 120
    assert back.downtimes[0].note == "squall"


def test_an_interruption_can_be_added_afterwards(open_book: sqlite3.Connection) -> None:
    shifts.add(open_book, a_shift())
    shifts.stop(open_book, "SH-00021", a_stop())
    assert shifts.get(open_book, "SH-00021").down_minutes == 120


def test_two_interruptions_that_overlap_are_refused(open_book: sqlite3.Connection) -> None:
    shifts.add(open_book, a_shift("SH-00021", DAY, a_stop()))
    with pytest.raises(Exception, match="overlap"):
        shifts.stop(open_book, "SH-00021", a_stop())


def test_stopping_a_shift_that_is_not_there_says_so(open_book: sqlite3.Connection) -> None:
    with pytest.raises(MissingError):
        shifts.stop(open_book, "SH-00099", a_stop())


def test_a_shift_on_a_dredge_that_is_not_there_is_refused(
    open_book: sqlite3.Connection,
) -> None:
    away = Shift("SH-00022", "DR-009", "RCH-012", moment(DAY, "06:00"), moment(DAY, "18:00"))
    with pytest.raises(MissingError):
        shifts.add(open_book, away)


def test_the_same_shift_twice_is_a_duplicate(open_book: sqlite3.Connection) -> None:
    shifts.add(open_book, a_shift())
    with pytest.raises(DuplicateError):
        shifts.add(open_book, a_shift())


def test_a_period_takes_both_its_ends(open_book: sqlite3.Connection) -> None:
    shifts.add(open_book, a_shift("SH-00021", DAY))
    shifts.add(open_book, a_shift("SH-00022", NEXT))
    shifts.add(open_book, a_shift("SH-00023", dt.date(2025, 6, 9)))
    found = shifts.between(open_book, DAY, NEXT)
    assert [s.ident for s in found] == ["SH-00021", "SH-00022"]


def test_shifts_of_a_reach_come_back_oldest_first(open_book: sqlite3.Connection) -> None:
    shifts.add(open_book, a_shift("SH-00022", NEXT))
    shifts.add(open_book, a_shift("SH-00021", DAY))
    assert [s.ident for s in shifts.for_reach(open_book, "RCH-012")] == [
        "SH-00021",
        "SH-00022",
    ]
    assert shifts.for_reach(open_book, "RCH-999") == ()
