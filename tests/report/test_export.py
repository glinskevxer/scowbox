"""The export writes plain numbers a spreadsheet can add up."""

from __future__ import annotations

import csv
import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.model.channel import Method, Reach, Template
from scowbox.model.contract import Contract, LineItem, Unit
from scowbox.model.placement import Grade, Ground, PlacementArea, PlacementTicket
from scowbox.model.plant import Dredge, Plant
from scowbox.model.scow import BoxReading, Corner, Scow, ScowTrip
from scowbox.model.shift import Shift
from scowbox.model.survey import Survey, SurveyKind
from scowbox.pay.estimate import build
from scowbox.report.export import sheets, write
from scowbox.store import (
    contracts,
    estimates,
    placements,
    reaches,
    scows,
    shifts,
    surveys,
    trips,
)
from scowbox.store.book import book
from scowbox.units.clock import moment
from scowbox.units.depth import Depth
from scowbox.units.money import Money
from scowbox.units.station import Reachline
from scowbox.units.volume import Yards

DAY = dt.date(2025, 10, 6)


@pytest.fixture
def open_book(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with book(tmp_path / "book.sqlite3", create=True) as connection:
        contract = Contract(
            number="W912PM-25-C-0014",
            awarded=dt.date(2025, 1, 20),
            notice_to_proceed=dt.date(2025, 2, 3),
            days=365,
            retainage=0.05,
            liquidated=Money.parse("$3,400.00"),
            items=(
                LineItem(
                    "LI-0001", "Dredging, base", Unit.CUBIC_YARD, Money.parse("$7.35"), "base"
                ),
            ),
        )
        contracts.add(connection, contract)
        reaches.add(
            connection,
            Reach(
                ident="RCH-012",
                name="Lower Range",
                line=Reachline.parse("100+00", "140+00"),
                template=Template(
                    bottom_width=400,
                    authorized_depth=Depth.of_feet(42),
                    side_slope=3,
                    advance_maintenance=2,
                    overdepth=2,
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
        trips.add(connection, ScowTrip("TR-04190", "SC-004", "RCH-012", DAY, "PA-002"))
        trips.release(
            connection,
            PlacementTicket(
                "TR-04188", "PA-002", moment(DAY, "11:20"), Yards.of_yards(2240), Grade.SUITABLE
            ),
        )
        estimates.add(
            connection,
            build(contract, 1, DAY, {"base": Yards.of_yards(1000)}),
        )
        yield connection


def read(where: Path, name: str) -> list[dict[str, str]]:
    with (where / f"{name}.csv").open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_every_sheet_is_written(open_book: sqlite3.Connection, tmp_path: Path) -> None:
    written = write(open_book, tmp_path / "out")
    assert [p.name for p in written] == [
        "reaches.csv",
        "surveys.csv",
        "trips.csv",
        "shifts.csv",
        "estimates.csv",
    ]


def test_the_directory_is_made_if_it_is_not_there(
    open_book: sqlite3.Connection, tmp_path: Path
) -> None:
    write(open_book, tmp_path / "deep" / "out")
    assert (tmp_path / "deep" / "out" / "reaches.csv").exists()


def test_the_reach_sheet_carries_the_three_depths(
    open_book: sqlite3.Connection, tmp_path: Path
) -> None:
    write(open_book, tmp_path / "out")
    row = read(tmp_path / "out", "reaches")[0]
    assert row["reach"] == "RCH-012"
    assert row["authorized_ft"] == "42.00"
    assert row["required_ft"] == "44.00"
    assert row["pay_ft"] == "46.00"


def test_numbers_are_written_plain(open_book: sqlite3.Connection, tmp_path: Path) -> None:
    write(open_book, tmp_path / "out")
    row = read(tmp_path / "out", "reaches")[0]
    assert row["length_ft"] == "4000.00"
    assert "," not in row["length_ft"]


def test_the_trip_sheet_measures_what_was_measured(
    open_book: sqlite3.Connection, tmp_path: Path
) -> None:
    write(open_book, tmp_path / "out")
    rows = {row["trip"]: row for row in read(tmp_path / "out", "trips")}
    assert rows["TR-04188"]["scow_yards"] == "2240.00"
    assert rows["TR-04188"]["placement"] == "PA-002"


def test_an_unmeasured_trip_leaves_the_cells_empty(
    open_book: sqlite3.Connection, tmp_path: Path
) -> None:
    write(open_book, tmp_path / "out")
    rows = {row["trip"]: row for row in read(tmp_path / "out", "trips")}
    assert rows["TR-04190"]["scow_yards"] == ""
    assert rows["TR-04190"]["placement"] == ""


def test_the_survey_sheet_counts_the_shots(open_book: sqlite3.Connection, tmp_path: Path) -> None:
    write(open_book, tmp_path / "out")
    assert read(tmp_path / "out", "surveys")[0]["soundings"] == "0"


def test_the_shift_sheet_carries_the_hours(open_book: sqlite3.Connection, tmp_path: Path) -> None:
    write(open_book, tmp_path / "out")
    row = read(tmp_path / "out", "shifts")[0]
    assert row["gross_hours"] == "12.00"
    assert row["effective_hours"] == "12.00"


def test_the_estimate_sheet_writes_money_as_a_decimal(
    open_book: sqlite3.Connection, tmp_path: Path
) -> None:
    write(open_book, tmp_path / "out")
    row = read(tmp_path / "out", "estimates")[0]
    assert row["unit_price"] == "7.35"
    assert row["earned"] == "7350.00"
    assert "$" not in row["earned"]


def test_an_empty_book_still_writes_headings(tmp_path: Path) -> None:
    with book(tmp_path / "empty.sqlite3", create=True) as connection:
        write(connection, tmp_path / "out")
    assert read(tmp_path / "out", "reaches") == []
    assert (tmp_path / "out" / "reaches.csv").read_text(encoding="utf-8").startswith("reach,")


def test_the_sheets_come_in_a_fixed_order(open_book: sqlite3.Connection) -> None:
    assert [s.name for s in sheets(open_book)] == [
        "reaches",
        "surveys",
        "trips",
        "shifts",
        "estimates",
    ]
