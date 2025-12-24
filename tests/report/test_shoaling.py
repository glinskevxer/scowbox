"""The shoaling report, and the reaches it cannot give a rate for."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.datum.tide import TideReading
from scowbox.model.channel import Method, Reach, Template
from scowbox.model.plant import Dredge, Plant
from scowbox.model.shift import Shift
from scowbox.model.survey import Sounding, Survey, SurveyKind
from scowbox.report.shoaling import intervals, render
from scowbox.store import reaches, shifts, surveys, tides
from scowbox.store.book import book
from scowbox.units.clock import moment
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline, Station

DAYS = [dt.date(2025, 1, 6), dt.date(2025, 6, 6), dt.date(2025, 12, 6)]
STATIONS = ["100+00", "101+00", "102+00", "103+00"]


def a_survey(ident: str, day: dt.date, depth: float) -> Survey:
    return Survey(
        ident=ident,
        reach="RCH-012",
        kind=SurveyKind.AFTER,
        taken_on=day,
        vessel="Cape Fear",
        transducer_draft=2.0,
        gauge="8658120",
        soundings=tuple(
            Sounding(
                station=Station.parse(station),
                offset=offset,
                raw_depth=Depth.of_feet(depth),
                taken=moment(day, "07:00"),
            )
            for station in STATIONS
            for offset in (-300.0, 0.0, 300.0)
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
                line=Reachline.parse("100+00", "103+00"),
                template=Template(
                    bottom_width=600,
                    authorized_depth=Depth.of_feet(42),
                    side_slope=0,
                    advance_maintenance=2,
                    overdepth=2,
                ),
                method=Method.SURVEY,
                group="base",
            ),
        )
        shifts.add_dredge(
            connection, Dredge("DR-003", "Cherokee", Plant.MECHANICAL, "Norfolk Dredging")
        )
        for day in DAYS:
            tides.add_readings(
                connection,
                "8658120",
                [
                    TideReading(moment(day, "06:54"), 2.0),
                    TideReading(moment(day, "07:06"), 2.0),
                ],
            )
        yield connection


def load(connection: sqlite3.Connection) -> None:
    for number, (day, depth) in enumerate(zip(DAYS, [46.0, 45.0, 44.0], strict=True)):
        surveys.add(connection, a_survey(f"SV-{number + 1:04d}", day, depth))


def text(connection: sqlite3.Connection) -> str:
    return "\n".join(render(connection))


def test_the_report_states_the_interval_it_used(open_book: sqlite3.Connection) -> None:
    assert "at least 30 days with no shift on the reach" in text(open_book)


def test_a_reach_with_no_quiet_interval_is_named(open_book: sqlite3.Connection) -> None:
    out = text(open_book)
    assert "No reach has a quiet interval to measure over." in out
    assert "RCH-012" in out


def test_a_measured_reach_gets_a_rate(open_book: sqlite3.Connection) -> None:
    load(open_book)
    out = text(open_book)
    assert "RCH-012" in out
    assert "cy a year" in out
    assert "SV-0002" in out


def test_a_reach_worked_throughout_falls_back_to_the_note(
    open_book: sqlite3.Connection,
) -> None:
    load(open_book)
    for number, day in enumerate((dt.date(2025, 3, 3), dt.date(2025, 9, 3))):
        shifts.add(
            open_book,
            Shift(
                f"SH-{number + 1:05d}",
                "DR-003",
                "RCH-012",
                moment(day, "06:00"),
                moment(day, "18:00"),
            ),
        )
    out = text(open_book)
    assert "quiet interval" in out


def test_the_intervals_of_a_reach_can_be_listed(open_book: sqlite3.Connection) -> None:
    load(open_book)
    lines = intervals(open_book, "RCH-012")
    assert lines[0].startswith("SV-0001 to SV-0002")
    assert "151 days" in lines[0]


def test_a_reach_with_none_says_so(open_book: sqlite3.Connection) -> None:
    assert intervals(open_book, "RCH-012") == ["RCH-012 has no interval nobody dredged it in."]
