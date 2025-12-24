"""Which pair of surveys a shoaling rate is taken between."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.datum.tide import TideReading
from scowbox.errors import MissingError
from scowbox.job.history import every_shoaling, latest_shoaling, quiet_pairs
from scowbox.model.channel import Method, Reach, Template
from scowbox.model.plant import Dredge, Plant
from scowbox.model.shift import Shift
from scowbox.model.survey import Sounding, Survey, SurveyKind
from scowbox.store import reaches, shifts, surveys, tides
from scowbox.store.book import book
from scowbox.units.clock import moment
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline, Station

DAYS = [dt.date(2025, 1, 6), dt.date(2025, 6, 6), dt.date(2025, 12, 6)]
STATIONS = ["100+00", "101+00", "102+00", "103+00"]


def a_survey(ident: str, day: dt.date, depth: float, gauge: str = "8658120") -> Survey:
    return Survey(
        ident=ident,
        reach="RCH-012",
        kind=SurveyKind.AFTER,
        taken_on=day,
        vessel="Cape Fear",
        transducer_draft=2.0,
        gauge=gauge,
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


def load(connection: sqlite3.Connection, depths: list[float]) -> None:
    for number, (day, depth) in enumerate(zip(DAYS, depths, strict=True)):
        surveys.add(connection, a_survey(f"SV-{number + 1:04d}", day, depth))


def a_shift(connection: sqlite3.Connection, day: dt.date) -> None:
    shifts.add(
        connection,
        Shift("SH-00021", "DR-003", "RCH-012", moment(day, "06:00"), moment(day, "18:00")),
    )


def test_consecutive_surveys_make_a_pair(open_book: sqlite3.Connection) -> None:
    load(open_book, [46.0, 45.0, 44.0])
    pairs = quiet_pairs(open_book, "RCH-012")
    assert [(a.ident, b.ident) for a, b in pairs] == [
        ("SV-0001", "SV-0002"),
        ("SV-0002", "SV-0003"),
    ]


def test_an_interval_with_a_shift_in_it_is_not_quiet(
    open_book: sqlite3.Connection,
) -> None:
    load(open_book, [46.0, 45.0, 44.0])
    a_shift(open_book, dt.date(2025, 3, 3))
    pairs = quiet_pairs(open_book, "RCH-012")
    assert [(a.ident, b.ident) for a, b in pairs] == [("SV-0002", "SV-0003")]


def test_a_short_interval_is_left_out(open_book: sqlite3.Connection) -> None:
    load(open_book, [46.0, 45.0, 44.0])
    surveys.add(open_book, a_survey("SV-0004", dt.date(2025, 12, 20), 44.0))
    tides.add_readings(
        open_book,
        "8658120",
        [
            TideReading(moment(dt.date(2025, 12, 20), "06:54"), 2.0),
            TideReading(moment(dt.date(2025, 12, 20), "07:06"), 2.0),
        ],
    )
    pairs = quiet_pairs(open_book, "RCH-012")
    assert ("SV-0003", "SV-0004") not in [(a.ident, b.ident) for a, b in pairs]


def test_a_survey_with_no_gauge_is_left_out(open_book: sqlite3.Connection) -> None:
    surveys.add(open_book, a_survey("SV-0001", DAYS[0], 46.0, gauge=""))
    surveys.add(open_book, a_survey("SV-0002", DAYS[1], 45.0))
    assert quiet_pairs(open_book, "RCH-012") == ()


def test_the_latest_quiet_interval_is_the_one_taken(
    open_book: sqlite3.Connection,
) -> None:
    load(open_book, [46.0, 45.0, 44.0])
    found = latest_shoaling(open_book, "RCH-012")
    assert (found.earlier, found.later) == ("SV-0002", "SV-0003")
    assert found.filling


def test_a_reach_with_no_quiet_interval_says_so(open_book: sqlite3.Connection) -> None:
    with pytest.raises(MissingError):
        latest_shoaling(open_book, "RCH-012")


def test_every_reach_that_has_one_is_measured(open_book: sqlite3.Connection) -> None:
    load(open_book, [46.0, 45.0, 44.0])
    assert [s.reach for s in every_shoaling(open_book)] == ["RCH-012"]


def test_a_reach_without_one_is_left_out_of_the_sweep(
    open_book: sqlite3.Connection,
) -> None:
    assert every_shoaling(open_book) == ()
