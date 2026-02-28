"""The gauge report, and the surveys a gap strands."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.datum.tide import TideReading
from scowbox.model.channel import Method, Reach, Template
from scowbox.model.survey import Survey, SurveyKind
from scowbox.report.gauges import render
from scowbox.store import reaches, surveys, tides
from scowbox.store.book import book
from scowbox.units.clock import moment
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline

DAY = dt.date(2026, 2, 24)


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
                method=Method.SURVEY,
                group="base",
            ),
        )
        yield connection


def a_survey(connection: sqlite3.Connection, ident: str, gauge: str) -> None:
    surveys.add(
        connection,
        Survey(ident, "RCH-012", SurveyKind.BEFORE, DAY, "Cape Fear", 2.5, gauge),
    )


def readings(connection: sqlite3.Connection, gauge: str, clocks: list[str]) -> None:
    tides.add_readings(
        connection, gauge, [TideReading(moment(DAY, clock), 2.0) for clock in clocks]
    )


def text(connection: sqlite3.Connection) -> str:
    return "\n".join(render(connection))


def test_an_empty_book_says_it_holds_no_readings(open_book: sqlite3.Connection) -> None:
    out = text(open_book)
    assert "No gauge readings in this book." in out
    assert "Every survey in the book can be reduced." in out


def test_a_gauge_reports_its_span_and_its_surveys(open_book: sqlite3.Connection) -> None:
    readings(open_book, "8658120", ["07:00", "07:06"])
    a_survey(open_book, "SV-0031", "8658120")
    out = text(open_book)
    assert "8658120" in out
    assert "2026-02-24 07:00" in out


def test_a_gauge_with_no_gap_says_so(open_book: sqlite3.Connection) -> None:
    readings(open_book, "8658120", ["07:00", "07:06"])
    assert "No gauge has a gap in it." in text(open_book)


def test_a_wide_gap_is_reported_with_its_length(open_book: sqlite3.Connection) -> None:
    readings(open_book, "8658120", ["07:00", "09:00"])
    out = text(open_book)
    assert "1 gaps too wide" in out
    assert "120 minutes" in out


def test_a_survey_with_no_gauge_cannot_be_reduced(open_book: sqlite3.Connection) -> None:
    a_survey(open_book, "SV-0031", "")
    out = text(open_book)
    assert "cannot reduce 1 surveys" in out
    assert "names no gauge" in out


def test_a_survey_the_gauge_never_covered_cannot_be_reduced(
    open_book: sqlite3.Connection,
) -> None:
    readings(open_book, "8658120", ["07:00", "07:06"])
    surveys.add(
        open_book,
        Survey(
            "SV-0032",
            "RCH-012",
            SurveyKind.AFTER,
            dt.date(2026, 3, 30),
            "Cape Fear",
            2.5,
            "8658120",
        ),
    )
    assert "cannot reduce" in text(open_book)


def test_a_covered_survey_is_not_reported_as_trouble(
    open_book: sqlite3.Connection,
) -> None:
    readings(open_book, "8658120", ["00:00", "23:59"])
    a_survey(open_book, "SV-0031", "8658120")
    assert "Every survey in the book can be reduced." in text(open_book)
