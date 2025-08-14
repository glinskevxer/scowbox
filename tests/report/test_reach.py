"""The reach report shows both measurements where both were taken."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.boxmeasure.bulking import Bulking
from scowbox.datum.tide import TideReading
from scowbox.model.channel import Method, Reach, Template
from scowbox.model.placement import Ground, PlacementArea
from scowbox.model.scow import BoxReading, Corner, Scow, ScowTrip
from scowbox.model.survey import Sounding, Survey, SurveyKind
from scowbox.report.reach import render
from scowbox.store import placements, reaches, scows, surveys, tides, trips
from scowbox.store.book import book
from scowbox.units.clock import moment
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline, Station

BEFORE_DAY = dt.date(2025, 7, 1)
AFTER_DAY = dt.date(2025, 8, 1)
SILT = Bulking("silt", 1.20)
STATIONS = ["100+00", "101+00", "102+00", "103+00"]


def a_reach(method: Method = Method.SURVEY) -> Reach:
    return Reach(
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
        method=method,
        group="base",
    )


def a_survey(ident: str, kind: SurveyKind, day: dt.date, depth: float) -> Survey:
    return Survey(
        ident=ident,
        reach="RCH-012",
        kind=kind,
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
        reaches.add(connection, a_reach())
        for day in (BEFORE_DAY, AFTER_DAY):
            tides.add_readings(
                connection,
                "8658120",
                [
                    TideReading(moment(day, "06:54"), 2.0),
                    TideReading(moment(day, "07:06"), 2.0),
                ],
            )
        yield connection


def load_surveys(connection: sqlite3.Connection) -> None:
    surveys.add(connection, a_survey("SV-0031", SurveyKind.BEFORE, BEFORE_DAY, 38.0))
    surveys.add(connection, a_survey("SV-0032", SurveyKind.AFTER, AFTER_DAY, 42.0))


def load_trips(connection: sqlite3.Connection, loads: int, measured: int) -> None:
    scows.add(connection, Scow("SC-004", "Dixie 41", 180, 42, 14))
    placements.add(
        connection, PlacementArea("PA-002", "Wilmington ODMDS", Ground.OCEAN, "SAW-2019-01142")
    )
    for number in range(loads):
        readings = tuple(BoxReading(c, 12.0, 4.0) for c in Corner) if number < measured else ()
        trips.add(
            connection,
            ScowTrip(f"TR-{number + 1:05d}", "SC-004", "RCH-012", AFTER_DAY, "PA-002", readings),
        )


def text(connection: sqlite3.Connection) -> str:
    return "\n".join(render(connection, "RCH-012", SILT))


def test_the_report_heads_with_the_reach(open_book: sqlite3.Connection) -> None:
    assert text(open_book).startswith("Reach RCH-012  Lower Range")


def test_the_three_depths_are_printed(open_book: sqlite3.Connection) -> None:
    out = text(open_book)
    assert "authorized    42.00 ft" in out
    assert "required      44.00 ft" in out
    assert "pay           46.00 ft" in out


def test_an_unsurveyed_reach_says_so(open_book: sqlite3.Connection) -> None:
    out = text(open_book)
    assert "No survey of this reach." in out
    assert "No scow trip out of this reach." in out
    assert "not measured" in out


def test_surveys_are_listed_with_their_shot_counts(open_book: sqlite3.Connection) -> None:
    load_surveys(open_book)
    out = text(open_book)
    assert "SV-0031" in out
    assert "8658120" in out
    assert "12" in out


def test_a_measured_reach_prints_its_quantity(open_book: sqlite3.Connection) -> None:
    load_surveys(open_book)
    out = text(open_book)
    assert "governs       survey" in out
    assert "quantity      26,667 cy" in out


def test_trips_are_counted_measured_and_unmeasured(open_book: sqlite3.Connection) -> None:
    load_trips(open_book, loads=3, measured=2)
    out = text(open_book)
    assert "trips         3" in out
    assert "measured      2" in out
    assert "unmeasured    1" in out


def test_a_reach_measured_both_ways_shows_both_and_the_spread(
    open_book: sqlite3.Connection,
) -> None:
    reaches.remove(open_book, "RCH-012")
    reaches.add(open_book, a_reach(Method.BOTH))
    load_surveys(open_book)
    load_trips(open_book, loads=15, measured=15)
    out = text(open_book)
    assert "survey        26,667 cy" in out
    assert "spread" in out
    assert "scow" in out


def test_a_wide_disagreement_asks_for_reconciliation(
    open_book: sqlite3.Connection,
) -> None:
    reaches.remove(open_book, "RCH-012")
    reaches.add(open_book, a_reach(Method.BOTH))
    load_surveys(open_book)
    load_trips(open_book, loads=2, measured=2)
    out = text(open_book)
    assert "reconcile" in out
    assert "governs       lesser of the two" in out
