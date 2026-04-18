"""The overdepth report, and the stations it names."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.boxmeasure.bulking import Bulking
from scowbox.datum.tide import TideReading
from scowbox.model.channel import Method, Reach, Template
from scowbox.model.survey import Sounding, Survey, SurveyKind
from scowbox.report.overdepth import render, share_of
from scowbox.section.area import SectionArea
from scowbox.store import reaches, surveys, tides
from scowbox.store.book import book
from scowbox.units.clock import moment
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline, Station

BEFORE = dt.date(2026, 4, 6)
AFTER = dt.date(2026, 5, 4)
SILT = Bulking("silt", 1.20)
STATIONS = ["100+00", "101+00", "102+00", "103+00"]


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
        for day in (BEFORE, AFTER):
            tides.add_readings(
                connection,
                "8658120",
                [
                    TideReading(moment(day, "06:54"), 2.0),
                    TideReading(moment(day, "07:06"), 2.0),
                ],
            )
        yield connection


def load(connection: sqlite3.Connection, after: float) -> None:
    surveys.add(connection, a_survey("SV-0031", SurveyKind.BEFORE, BEFORE, 38.0))
    surveys.add(connection, a_survey("SV-0032", SurveyKind.AFTER, AFTER, after))


def text(connection: sqlite3.Connection, watch: float = 0.15) -> str:
    return "\n".join(render(connection, SILT, watch=watch))


def an_area(removed: float, pay: float) -> SectionArea:
    return SectionArea(Station.parse("100+00"), removed, pay, -300, 300)


def test_a_section_that_removed_nothing_has_no_share() -> None:
    assert share_of(an_area(0.0, 0.0)) == 0.0


def test_the_share_is_overcut_over_removed() -> None:
    assert share_of(an_area(1000.0, 800.0)) == 0.2


def test_a_book_with_no_survey_says_so(open_book: sqlite3.Connection) -> None:
    out = text(open_book)
    assert "No reach has a survey quantity" in out
    assert "no survey quantity to take an overcut from" in out


def test_a_cut_inside_the_prism_has_no_overcut(open_book: sqlite3.Connection) -> None:
    load(open_book, 42.0)
    out = text(open_book)
    assert "0 cy" in out
    assert "0.0%" in out


def test_a_cut_past_the_prism_shows_its_share(open_book: sqlite3.Connection) -> None:
    load(open_book, 48.0)
    out = text(open_book)
    assert "13,333 cy" in out
    assert "20.0%" in out


def test_a_reach_over_the_watch_names_its_stations(open_book: sqlite3.Connection) -> None:
    load(open_book, 48.0)
    out = text(open_book)
    assert "over the watch on 4 of 4 sections" in out
    assert "100+00" in out


def test_a_gentler_watch_leaves_it_alone(open_book: sqlite3.Connection) -> None:
    load(open_book, 48.0)
    assert "over the watch" not in text(open_book, watch=0.5)


def test_the_watch_is_printed_at_the_top(open_book: sqlite3.Connection) -> None:
    assert "watch above   15% of removed material" in text(open_book)
