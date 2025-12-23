"""The production report over a book with a couple of days in it."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.boxmeasure.bulking import Bulking
from scowbox.model.channel import Method, Reach, Template
from scowbox.model.placement import Ground, PlacementArea
from scowbox.model.plant import Dredge, Plant
from scowbox.model.scow import BoxReading, Corner, Scow, ScowTrip
from scowbox.model.shift import Shift
from scowbox.report.production import render
from scowbox.store import placements, reaches, scows, shifts, trips
from scowbox.store.book import book
from scowbox.units.clock import moment
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline

DAY = dt.date(2025, 12, 1)
NEXT = dt.date(2025, 12, 2)
SILT = Bulking("silt", 1.20)


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


def work(connection: sqlite3.Connection, day: dt.date, ident: str, loads: int, end: str) -> None:
    shifts.add(
        connection,
        Shift(ident, "DR-003", "RCH-012", moment(day, "06:00"), moment(day, end)),
    )
    for number in range(loads):
        trips.add(
            connection,
            ScowTrip(
                f"TR-{day.day:02d}{number + 1:03d}",
                "SC-004",
                "RCH-012",
                day,
                "PA-002",
                tuple(BoxReading(c, 12.0, 4.0) for c in Corner),
            ),
        )


def text(connection: sqlite3.Connection, reach: str | None = None) -> str:
    return "\n".join(render(connection, SILT, reach=reach))


def test_an_empty_book_says_so(open_book: sqlite3.Connection) -> None:
    out = text(open_book)
    assert "No shift or trip logged." in out
    assert "RCH-012       not measured" in out


def test_the_average_load_is_reported(open_book: sqlite3.Connection) -> None:
    work(open_book, DAY, "SH-00021", 2, "18:00")
    assert "average load  2,240 cy" in text(open_book)


def test_each_day_gets_a_row(open_book: sqlite3.Connection) -> None:
    work(open_book, DAY, "SH-00021", 2, "18:00")
    work(open_book, NEXT, "SH-00022", 4, "18:00")
    out = text(open_book)
    assert "2025-12-01" in out
    assert "2025-12-02" in out


def test_the_best_and_worst_days_are_named(open_book: sqlite3.Connection) -> None:
    work(open_book, DAY, "SH-00021", 2, "18:00")
    work(open_book, NEXT, "SH-00022", 4, "18:00")
    out = text(open_book)
    assert "best day      2025-12-02" in out
    assert "worst day     2025-12-01" in out


def test_the_reach_line_carries_the_quantity_and_the_rate(
    open_book: sqlite3.Connection,
) -> None:
    work(open_book, DAY, "SH-00021", 2, "18:00")
    out = text(open_book)
    assert "RCH-012" in out
    assert "cy an hour" in out


def test_the_report_can_be_narrowed_to_a_reach(open_book: sqlite3.Connection) -> None:
    work(open_book, DAY, "SH-00021", 2, "18:00")
    out = text(open_book, reach="RCH-012")
    assert out.startswith("Production, RCH-012")


def test_a_reach_nobody_worked_reports_no_days(open_book: sqlite3.Connection) -> None:
    work(open_book, DAY, "SH-00021", 2, "18:00")
    assert "No shift or trip logged." in text(open_book, reach="RCH-999")
