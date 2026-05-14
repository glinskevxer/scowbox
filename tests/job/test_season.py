"""Everything the book still has outstanding."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.boxmeasure.bulking import Bulking
from scowbox.job.season import closeout
from scowbox.model.channel import Method, Reach, Template
from scowbox.model.contract import Contract, LineItem, Unit
from scowbox.model.placement import Ground, PlacementArea
from scowbox.model.scow import Scow, ScowTrip
from scowbox.model.survey import Survey, SurveyKind
from scowbox.pay.estimate import build
from scowbox.store import contracts, estimates, placements, reaches, scows, surveys, trips
from scowbox.store.book import book
from scowbox.units.depth import Depth
from scowbox.units.money import Money
from scowbox.units.station import Reachline
from scowbox.units.volume import Yards

DAY = dt.date(2026, 5, 6)
SILT = Bulking("silt", 1.20)
NUMBER = "W912PM-25-C-0014"

CONTRACT = Contract(
    number=NUMBER,
    awarded=dt.date(2025, 1, 20),
    notice_to_proceed=dt.date(2025, 2, 3),
    days=730,
    retainage=0.05,
    liquidated=Money.parse("$3,400.00"),
    items=(LineItem("LI-0001", "Dredging", Unit.CUBIC_YARD, Money.parse("$7.35"), "base"),),
)


@pytest.fixture
def open_book(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with book(tmp_path / "book.sqlite3", create=True) as connection:
        contracts.add(connection, CONTRACT)
        yield connection


def a_reach(connection: sqlite3.Connection) -> None:
    reaches.add(
        connection,
        Reach(
            ident="RCH-012",
            name="Lower Range",
            line=Reachline.parse("100+00", "140+00"),
            template=Template(bottom_width=400, authorized_depth=Depth.of_feet(42), side_slope=3),
            method=Method.SCOW,
            group="base",
        ),
    )


def a_trip(connection: sqlite3.Connection) -> None:
    scows.add(connection, Scow("SC-004", "Dixie 41", 180, 42, 14))
    placements.add(
        connection,
        PlacementArea("PA-002", "Wilmington ODMDS", Ground.OCEAN, "SAW-2019-01142"),
    )
    trips.add(connection, ScowTrip("TR-04188", "SC-004", "RCH-012", DAY, "PA-002"))


def test_an_empty_book_has_nothing_outstanding(open_book: sqlite3.Connection) -> None:
    found = closeout(open_book, SILT)
    assert found.outstanding == 0
    assert found.closeable


def test_a_reach_nobody_measured_is_outstanding(open_book: sqlite3.Connection) -> None:
    a_reach(open_book)
    found = closeout(open_book, SILT)
    assert found.unmeasured[0][0] == "RCH-012"
    assert found.outstanding == 1
    assert not found.closeable


def test_a_trip_with_no_ticket_is_outstanding(open_book: sqlite3.Connection) -> None:
    a_reach(open_book)
    a_trip(open_book)
    found = closeout(open_book, SILT)
    assert found.unticketed == ("TR-04188",)
    assert found.warnings >= 1


def test_a_missing_ticket_becomes_a_violation_once_the_month_closes(
    open_book: sqlite3.Connection,
) -> None:
    a_reach(open_book)
    a_trip(open_book)
    found = closeout(open_book, SILT, closed_through=dt.date(2026, 5, 31))
    assert found.violations >= 1


def test_a_survey_with_no_gauge_cannot_be_reduced(open_book: sqlite3.Connection) -> None:
    a_reach(open_book)
    surveys.add(
        open_book,
        Survey("SV-0031", "RCH-012", SurveyKind.BEFORE, DAY, "Cape Fear", 2.5, ""),
    )
    found = closeout(open_book, SILT)
    assert found.unreduced[0][0] == "SV-0031"


def test_the_estimates_are_counted(open_book: sqlite3.Connection) -> None:
    estimates.add(open_book, build(CONTRACT, 1, DAY, {"base": Yards.of_yards(1000)}))
    found = closeout(open_book, SILT)
    assert found.estimates == 1
    assert not found.closed


def test_a_final_estimate_closes_the_contract(open_book: sqlite3.Connection) -> None:
    estimates.add(open_book, build(CONTRACT, 1, DAY, {"base": Yards.of_yards(1000)}, final=True))
    found = closeout(open_book, SILT)
    assert found.closed
    assert not found.closeable


def test_a_book_with_no_contract_counts_no_estimates(tmp_path: Path) -> None:
    with book(tmp_path / "empty.sqlite3", create=True) as connection:
        found = closeout(connection, SILT)
    assert found.estimates == 0
    assert not found.closed
