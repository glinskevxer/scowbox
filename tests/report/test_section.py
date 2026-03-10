"""The section sheet prints the arithmetic, not just the answer."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.datum.tide import TideReading
from scowbox.errors import RuleError
from scowbox.model.channel import Method, Reach, Template
from scowbox.model.survey import Sounding, Survey, SurveyKind
from scowbox.report.section import render
from scowbox.store import reaches, surveys, tides
from scowbox.store.book import book
from scowbox.units.clock import moment
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline, Station

BEFORE = dt.date(2026, 3, 2)
AFTER = dt.date(2026, 4, 6)
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


def load(connection: sqlite3.Connection, after: float = 42.0) -> None:
    surveys.add(connection, a_survey("SV-0031", SurveyKind.BEFORE, BEFORE, 38.0))
    surveys.add(connection, a_survey("SV-0032", SurveyKind.AFTER, AFTER, after))


def text(connection: sqlite3.Connection) -> str:
    return "\n".join(render(connection, "RCH-012"))


def test_the_sheet_names_both_surveys(open_book: sqlite3.Connection) -> None:
    load(open_book)
    out = text(open_book)
    assert out.startswith("Sections, RCH-012  Lower Range")
    assert "SV-0031 before, SV-0032 after" in out


def test_every_section_gets_a_row(open_book: sqlite3.Connection) -> None:
    load(open_book)
    out = text(open_book)
    for station in STATIONS:
        assert station in out


def test_every_slice_gets_a_row(open_book: sqlite3.Connection) -> None:
    load(open_book)
    out = text(open_book)
    assert out.count("100+00") >= 2
    assert "sections      4 of 4" in out


def test_the_totals_are_printed_three_ways(open_book: sqlite3.Connection) -> None:
    load(open_book)
    out = text(open_book)
    assert "cy removed" in out
    assert "cy pay" in out
    assert "cy overcut" in out


def test_a_cut_inside_the_prism_has_no_overcut(open_book: sqlite3.Connection) -> None:
    load(open_book)
    assert "0 cy overcut" in text(open_book)


def test_a_cut_past_the_prism_shows_the_overcut(open_book: sqlite3.Connection) -> None:
    load(open_book, after=48.0)
    out = text(open_book)
    assert "13,333 cy overcut" in out


def test_a_reach_with_no_surveys_cannot_be_sheeted(
    open_book: sqlite3.Connection,
) -> None:
    with pytest.raises(Exception, match="survey"):
        text(open_book)


def test_a_wider_interval_gives_fewer_sections(open_book: sqlite3.Connection) -> None:
    load(open_book)
    out = "\n".join(render(open_book, "RCH-012", interval=200.0))
    assert "sections      3 of 3" in out


def test_an_interval_that_lands_between_the_shots_is_refused(
    open_book: sqlite3.Connection,
) -> None:
    load(open_book)
    with pytest.raises(RuleError):
        render(open_book, "RCH-012", interval=150.0)
