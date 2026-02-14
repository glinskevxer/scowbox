"""Finding whatever an identifier turns out to name."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.datum.tide import TideReading
from scowbox.errors import MissingError
from scowbox.job.lookup import find
from scowbox.model.channel import Method, Reach, Template
from scowbox.model.contract import Contract, LineItem, Unit
from scowbox.model.placement import Grade, Ground, PlacementArea, PlacementTicket
from scowbox.model.plant import Dredge, Plant
from scowbox.model.scow import BoxReading, Corner, Scow, ScowTrip
from scowbox.model.shift import Shift
from scowbox.model.survey import Survey, SurveyKind
from scowbox.pay.estimate import build
from scowbox.store import (
    contracts,
    estimates,
    placements,
    reaches,
    scows,
    shifts,
    surveys,
    tides,
    trips,
)
from scowbox.store.book import book
from scowbox.units.clock import moment
from scowbox.units.depth import Depth
from scowbox.units.money import Money
from scowbox.units.station import Reachline
from scowbox.units.volume import Yards

DAY = dt.date(2026, 2, 16)
NUMBER = "W912PM-25-C-0014"


@pytest.fixture
def open_book(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with book(tmp_path / "book.sqlite3", create=True) as connection:
        contract = Contract(
            number=NUMBER,
            awarded=dt.date(2025, 1, 20),
            notice_to_proceed=dt.date(2025, 2, 3),
            days=365,
            retainage=0.05,
            liquidated=Money.parse("$3,400.00"),
            items=(LineItem("LI-0001", "Dredging", Unit.CUBIC_YARD, Money.parse("$7.35"), "base"),),
        )
        contracts.add(connection, contract)
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
        surveys.add(
            connection,
            Survey("SV-0031", "RCH-012", SurveyKind.BEFORE, DAY, "Cape Fear", 2.5, "8658120"),
        )
        scows.add(connection, Scow("SC-004", "Dixie 41", 180, 42, 14))
        placements.add(
            connection,
            PlacementArea("PA-002", "Wilmington ODMDS", Ground.OCEAN, "SAW-2019-01142"),
        )
        shifts.add_dredge(
            connection, Dredge("DR-003", "Cherokee", Plant.MECHANICAL, "Norfolk Dredging")
        )
        shifts.add(
            connection,
            Shift("SH-00021", "DR-003", "RCH-012", moment(DAY, "06:00"), moment(DAY, "18:00")),
        )
        trips.add(
            connection,
            ScowTrip(
                "TR-04188",
                "SC-004",
                "RCH-012",
                DAY,
                "PA-002",
                tuple(BoxReading(c, 12.0, 4.0) for c in Corner),
            ),
        )
        tides.add_readings(connection, "8658120", [TideReading(moment(DAY, "07:00"), 2.0)])
        estimates.add(connection, build(contract, 1, DAY, {"base": Yards.of_yards(1000)}))
        yield connection


def text(connection: sqlite3.Connection, wanted: str) -> str:
    return "\n".join(find(connection, wanted))


def test_a_reach_is_described_with_what_is_against_it(
    open_book: sqlite3.Connection,
) -> None:
    out = text(open_book, "RCH-012")
    assert "RCH-012 Lower Range" in out
    assert "1 surveys, 1 trips, 1 shifts" in out


def test_a_survey_names_its_reach_and_its_gauge(open_book: sqlite3.Connection) -> None:
    out = text(open_book, "SV-0031")
    assert "before survey of RCH-012" in out
    assert "gauge 8658120" in out


def test_a_scow_counts_its_trips(open_book: sqlite3.Connection) -> None:
    assert "1 trips" in text(open_book, "SC-004")


def test_a_trip_says_whether_it_was_ticketed(open_book: sqlite3.Connection) -> None:
    assert "no placement ticket" in text(open_book, "TR-04188")
    trips.release(
        open_book,
        PlacementTicket(
            "TR-04188", "PA-002", moment(DAY, "11:20"), Yards.of_yards(2240), Grade.SUITABLE
        ),
    )
    assert "released at PA-002" in text(open_book, "TR-04188")


def test_a_placement_area_counts_its_loads(open_book: sqlite3.Connection) -> None:
    assert "0 loads" in text(open_book, "PA-002")


def test_a_dredge_counts_its_shifts(open_book: sqlite3.Connection) -> None:
    assert "1 shifts" in text(open_book, "DR-003")


def test_a_shift_reports_its_hours(open_book: sqlite3.Connection) -> None:
    assert "12.00 gross" in text(open_book, "SH-00021")


def test_an_estimate_reports_its_money(open_book: sqlite3.Connection) -> None:
    assert "earned $7,350.00" in text(open_book, "EST-001")


def test_a_contract_number_is_found_without_a_prefix(
    open_book: sqlite3.Connection,
) -> None:
    out = text(open_book, NUMBER)
    assert "365 days" in out
    assert "1 line items" in out


def test_a_gauge_number_is_found_without_a_prefix(
    open_book: sqlite3.Connection,
) -> None:
    assert "readings from 2026-02-16" in text(open_book, "8658120")


def test_something_that_is_nothing_says_so(open_book: sqlite3.Connection) -> None:
    with pytest.raises(MissingError):
        find(open_book, "nothing at all")


def test_a_well_formed_identifier_that_is_not_there_still_raises(
    open_book: sqlite3.Connection,
) -> None:
    with pytest.raises(MissingError):
        find(open_book, "RCH-999")


def test_surrounding_space_is_ignored(open_book: sqlite3.Connection) -> None:
    assert "Lower Range" in text(open_book, "  RCH-012  ")
