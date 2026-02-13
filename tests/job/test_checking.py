"""Reading a survey in the book back against its own reach's template."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.datum.tide import TideReading
from scowbox.errors import RuleError
from scowbox.job.checking import check_survey
from scowbox.model.channel import Method, Reach, Template
from scowbox.model.survey import Sounding, Survey, SurveyKind
from scowbox.store import reaches, surveys, tides
from scowbox.store.book import book
from scowbox.units.clock import moment
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline, Station

DAY = dt.date(2026, 2, 9)


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
                    bottom_width=600, authorized_depth=Depth.of_feet(42), side_slope=0
                ),
                method=Method.SURVEY,
                group="base",
            ),
        )
        tides.add_readings(
            connection,
            "8658120",
            [
                TideReading(moment(DAY, "06:54"), 2.0),
                TideReading(moment(DAY, "07:06"), 2.0),
            ],
        )
        yield connection


def load(
    connection: sqlite3.Connection, shots: list[tuple[str, float, float]], gauge: str = "8658120"
) -> None:
    surveys.add(
        connection,
        Survey(
            ident="SV-0031",
            reach="RCH-012",
            kind=SurveyKind.BEFORE,
            taken_on=DAY,
            vessel="Cape Fear",
            transducer_draft=2.0,
            gauge=gauge,
            soundings=tuple(
                Sounding(
                    station=Station.parse(station),
                    offset=offset,
                    raw_depth=Depth.of_feet(depth),
                    taken=moment(DAY, "07:00"),
                )
                for station, offset, depth in shots
            ),
        ),
    )


def a_line(station: str, depth: float = 44.0) -> list[tuple[str, float, float]]:
    return [(station, offset, depth) for offset in (-300.0, 0.0, 300.0)]


def test_a_clean_survey_reads_sound(open_book: sqlite3.Connection) -> None:
    load(open_book, [*a_line("100+00"), *a_line("101+00")])
    got = check_survey(open_book, "SV-0031")
    assert got.sound
    assert got.shots == 6


def test_a_survey_that_disagrees_with_itself_is_not_sound(
    open_book: sqlite3.Connection,
) -> None:
    load(open_book, [*a_line("100+00"), ("100+00", 0.0, 45.0)])
    got = check_survey(open_book, "SV-0031")
    assert not got.repeatable
    assert got.worst == pytest.approx(1.0, abs=0.01)


def test_the_template_comes_off_the_reach_the_survey_was_run_over(
    open_book: sqlite3.Connection,
) -> None:
    load(open_book, [("100+00", -100.0, 44.0), ("100+00", 100.0, 44.0)])
    got = check_survey(open_book, "SV-0031")
    assert not got.covered
    assert got.short[0][2] == 540.0


def test_a_gentler_share_accepts_the_same_survey(
    open_book: sqlite3.Connection,
) -> None:
    load(open_book, [("100+00", -200.0, 44.0), ("100+00", 200.0, 44.0)])
    assert check_survey(open_book, "SV-0031", share=0.6).covered


def test_a_survey_with_no_gauge_cannot_be_checked(
    open_book: sqlite3.Connection,
) -> None:
    load(open_book, a_line("100+00"), gauge="")
    with pytest.raises(RuleError):
        check_survey(open_book, "SV-0031")
