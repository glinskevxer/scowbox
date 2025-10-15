"""The season report and the audit, over a book with a little of everything."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.boxmeasure.bulking import Bulking
from scowbox.model.channel import Method, Reach, Template
from scowbox.model.contract import Contract, LineItem, Unit
from scowbox.model.placement import Ground, PlacementArea
from scowbox.model.plant import Dredge, Plant
from scowbox.model.scow import BoxReading, Corner, Scow, ScowTrip
from scowbox.model.shift import Downtime, Reason, Shift
from scowbox.model.window import Restriction, Window
from scowbox.report.audit import render as audit
from scowbox.report.season import render as season
from scowbox.store import contracts, placements, reaches, scows, shifts, trips, windows
from scowbox.store.book import book
from scowbox.units.clock import moment
from scowbox.units.depth import Depth
from scowbox.units.money import Money
from scowbox.units.station import Reachline

DAY = dt.date(2025, 8, 6)
SILT = Bulking("silt", 1.20)

CONTRACT = Contract(
    number="W912PM-25-C-0014",
    awarded=dt.date(2025, 1, 20),
    notice_to_proceed=dt.date(2025, 2, 3),
    days=365,
    retainage=0.05,
    liquidated=Money.parse("$3,400.00"),
    items=(
        LineItem(
            "LI-0001", "Dredging, base", Unit.CUBIC_YARD, Money.parse("$7.35"), "base", 480000
        ),
    ),
)


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
        scows.add(connection, Scow("SC-004", "Dixie 41", 180, 42, 14))
        placements.add(
            connection,
            PlacementArea("PA-002", "Wilmington ODMDS", Ground.OCEAN, "SAW-2019-01142"),
        )
        shifts.add_dredge(
            connection, Dredge("DR-003", "Cherokee", Plant.MECHANICAL, "Norfolk Dredging")
        )
        yield connection


def a_trip(connection: sqlite3.Connection, ident: str = "TR-04188") -> None:
    trips.add(
        connection,
        ScowTrip(
            ident,
            "SC-004",
            "RCH-012",
            DAY,
            "PA-002",
            tuple(BoxReading(c, 12.0, 4.0) for c in Corner),
        ),
    )


def a_shift(connection: sqlite3.Connection, *stops: Downtime) -> None:
    shifts.add(
        connection,
        Shift("SH-00021", "DR-003", "RCH-012", moment(DAY, "06:00"), moment(DAY, "18:00"), stops),
    )


def text(connection: sqlite3.Connection) -> str:
    return "\n".join(season(connection, SILT))


def test_the_season_counts_what_is_in_the_book(open_book: sqlite3.Connection) -> None:
    out = text(open_book)
    assert "reaches       1" in out
    assert "measured to   nothing measured" in out


def test_an_empty_book_has_nothing_measured(open_book: sqlite3.Connection) -> None:
    out = text(open_book)
    assert "Nothing measured yet." in out
    assert "No shift logged." in out
    assert "No contract in this book." in out


def test_a_measured_reach_reaches_the_group_table(open_book: sqlite3.Connection) -> None:
    a_trip(open_book)
    out = text(open_book)
    assert "base" in out
    assert "1,867 cy" in out


def test_the_bid_quantity_and_the_price_come_off_the_contract(
    open_book: sqlite3.Connection,
) -> None:
    contracts.add(open_book, CONTRACT)
    a_trip(open_book)
    out = text(open_book)
    assert "480,000" in out
    assert "$13,720" in out


def test_shift_hours_are_summed(open_book: sqlite3.Connection) -> None:
    a_shift(open_book, Downtime(moment(DAY, "09:00"), moment(DAY, "11:00"), Reason.WEATHER))
    out = text(open_book)
    assert "gross         12.00 hours" in out
    assert "allowable     2.00 hours" in out


def test_an_unmeasured_reach_is_named(open_book: sqlite3.Connection) -> None:
    reaches.add(
        open_book,
        Reach(
            ident="RCH-014",
            name="Entrance",
            line=Reachline.parse("200+00", "240+00"),
            template=Template(bottom_width=400, authorized_depth=Depth.of_feet(42), side_slope=3),
            method=Method.SURVEY,
            group="entrance",
        ),
    )
    a_trip(open_book)
    out = text(open_book)
    assert "1 reaches not measured yet" in out
    assert "RCH-014" in out


def test_a_group_with_no_line_item_says_so(open_book: sqlite3.Connection) -> None:
    contracts.add(open_book, CONTRACT)
    reaches.add(
        open_book,
        Reach(
            ident="RCH-014",
            name="Entrance",
            line=Reachline.parse("200+00", "240+00"),
            template=Template(bottom_width=400, authorized_depth=Depth.of_feet(42), side_slope=3),
            method=Method.SCOW,
            group="entrance",
        ),
    )
    trips.add(
        open_book,
        ScowTrip(
            "TR-04190",
            "SC-004",
            "RCH-014",
            DAY,
            "PA-002",
            tuple(BoxReading(c, 12.0, 4.0) for c in Corner),
        ),
    )
    a_trip(open_book)
    out = text(open_book)
    assert "no item" in out


def test_two_contracts_leave_the_pricing_out(open_book: sqlite3.Connection) -> None:
    contracts.add(open_book, CONTRACT)
    contracts.add(
        open_book,
        Contract(
            number="W912PM-25-C-0020",
            awarded=dt.date(2025, 1, 20),
            notice_to_proceed=dt.date(2025, 2, 3),
            days=365,
            retainage=0.05,
            liquidated=Money.parse("$3,400.00"),
        ),
    )
    a_trip(open_book)
    out = text(open_book)
    assert "No contract in this book." in out


def test_a_clean_book_audits_clean(open_book: sqlite3.Connection) -> None:
    assert "Nothing outstanding." in "\n".join(audit(open_book))


def test_the_audit_counts_what_it_swept(open_book: sqlite3.Connection) -> None:
    a_trip(open_book)
    a_shift(open_book)
    out = "\n".join(audit(open_book))
    assert "shifts        1" in out
    assert "trips         1" in out


def test_a_missing_ticket_is_a_warning_then_a_violation(
    open_book: sqlite3.Connection,
) -> None:
    a_trip(open_book)
    assert "1 warnings" in "\n".join(audit(open_book))
    assert "1 violations" in "\n".join(audit(open_book, dt.date(2025, 8, 31)))


def test_a_closure_shows_in_the_audit(open_book: sqlite3.Connection) -> None:
    windows.add(
        open_book,
        Window(
            "loggerhead", dt.date(2025, 5, 1), dt.date(2025, 11, 30), Restriction.CLOSED, "NMFS"
        ),
    )
    a_shift(open_book)
    out = "\n".join(audit(open_book))
    assert "loggerhead" in out
    assert "violation" in out
