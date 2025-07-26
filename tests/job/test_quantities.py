"""Working quantities out of a book that holds the whole record."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.boxmeasure.bulking import Bulking
from scowbox.datum.tide import TideReading
from scowbox.errors import MissingError, RuleError
from scowbox.job.quantities import (
    by_group,
    determine_reach,
    last_survey,
    measured_through,
    tide_for,
    unmeasured,
)
from scowbox.measure.governing import Governs
from scowbox.model.channel import Method, Reach, Template
from scowbox.model.placement import Ground, PlacementArea
from scowbox.model.scow import BoxReading, Corner, Scow, ScowTrip
from scowbox.model.survey import Sounding, Survey, SurveyKind
from scowbox.store import placements, reaches, scows, surveys, tides, trips
from scowbox.store.book import book
from scowbox.units.clock import moment
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline, Station
from scowbox.units.volume import Yards

BEFORE_DAY = dt.date(2025, 7, 1)
AFTER_DAY = dt.date(2025, 8, 1)
STATIONS = ["100+00", "101+00", "102+00", "103+00"]
SILT = Bulking("silt", 1.20)


def a_reach(ident: str = "RCH-012", method: Method = Method.SURVEY, group: str = "base") -> Reach:
    return Reach(
        ident=ident,
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
        group=group,
    )


def shots(day: dt.date, depth: float) -> tuple[Sounding, ...]:
    return tuple(
        Sounding(
            station=Station.parse(station),
            offset=offset,
            raw_depth=Depth.of_feet(depth),
            taken=moment(day, "07:00"),
        )
        for station in STATIONS
        for offset in (-300.0, 0.0, 300.0)
    )


def a_survey(ident: str, kind: SurveyKind, day: dt.date, depth: float, gauge: str = "8658120"):  # type: ignore[no-untyped-def]
    return Survey(
        ident=ident,
        reach="RCH-012",
        kind=kind,
        taken_on=day,
        vessel="Cape Fear",
        transducer_draft=2.0,
        gauge=gauge,
        soundings=shots(day, depth),
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


def load_surveys(connection: sqlite3.Connection, before: float = 38.0, after: float = 42.0) -> None:
    surveys.add(connection, a_survey("SV-0031", SurveyKind.BEFORE, BEFORE_DAY, before))
    surveys.add(connection, a_survey("SV-0032", SurveyKind.AFTER, AFTER_DAY, after))


def load_scows(connection: sqlite3.Connection, loads: int = 1) -> None:
    scows.add(connection, Scow("SC-004", "Dixie 41", 180, 42, 14))
    placements.add(
        connection, PlacementArea("PA-002", "Wilmington ODMDS", Ground.OCEAN, "SAW-2019-01142")
    )
    for number in range(loads):
        trips.add(
            connection,
            ScowTrip(
                ident=f"TR-{number + 1:05d}",
                scow="SC-004",
                reach="RCH-012",
                loaded_on=AFTER_DAY,
                placement="PA-002",
                readings=tuple(BoxReading(corner, 12.0, 4.0) for corner in Corner),
            ),
        )


def test_the_last_survey_of_a_kind_is_the_one_taken(open_book: sqlite3.Connection) -> None:
    load_surveys(open_book)
    surveys.add(open_book, a_survey("SV-0033", SurveyKind.BEFORE, dt.date(2025, 7, 15), 39.0))
    assert last_survey(open_book, "RCH-012", SurveyKind.BEFORE).ident == "SV-0033"


def test_a_reach_with_no_survey_of_that_kind_says_so(open_book: sqlite3.Connection) -> None:
    with pytest.raises(MissingError):
        last_survey(open_book, "RCH-012", SurveyKind.AFTER)


def test_a_survey_with_no_gauge_cannot_be_reduced(open_book: sqlite3.Connection) -> None:
    surveys.add(open_book, a_survey("SV-0041", SurveyKind.BEFORE, BEFORE_DAY, 38.0, gauge=""))
    with pytest.raises(RuleError, match="names no gauge"):
        tide_for(open_book, surveys.get(open_book, "SV-0041"))


def test_a_survey_reach_determines_from_the_survey(open_book: sqlite3.Connection) -> None:
    load_surveys(open_book)
    got = determine_reach(open_book, "RCH-012", SILT)
    assert got.governs is Governs.SURVEY
    assert got.quantity.yards == pytest.approx(4 * 600 * 300 / 27, abs=0.05)


def test_a_scow_reach_determines_from_the_trips(open_book: sqlite3.Connection) -> None:
    reaches.remove(open_book, "RCH-012")
    reaches.add(open_book, a_reach(method=Method.SCOW))
    load_scows(open_book, loads=2)
    got = determine_reach(open_book, "RCH-012", SILT)
    assert got.governs is Governs.SCOW
    assert got.survey is None


def test_a_both_reach_takes_the_two_and_compares_them(open_book: sqlite3.Connection) -> None:
    reaches.remove(open_book, "RCH-012")
    reaches.add(open_book, a_reach(method=Method.BOTH))
    load_surveys(open_book)
    load_scows(open_book, loads=12)
    got = determine_reach(open_book, "RCH-012", SILT)
    assert got.survey is not None
    assert got.scow is not None
    assert got.spread is not None


def test_a_deduction_reaches_the_scow_side(open_book: sqlite3.Connection) -> None:
    reaches.remove(open_book, "RCH-012")
    reaches.add(open_book, a_reach(method=Method.SCOW))
    load_scows(open_book, loads=2)
    plain = determine_reach(open_book, "RCH-012", SILT)
    docked = determine_reach(open_book, "RCH-012", SILT, deduction=0.2)
    assert docked.quantity < plain.quantity


def test_quantities_gather_into_pay_groups(open_book: sqlite3.Connection) -> None:
    load_surveys(open_book)
    gathered = by_group(open_book, SILT)
    assert set(gathered) == {"base"}
    assert gathered["base"].yards == pytest.approx(4 * 600 * 300 / 27, abs=0.05)


def test_two_reaches_in_one_group_add_up(open_book: sqlite3.Connection) -> None:
    load_surveys(open_book)
    reaches.add(
        open_book,
        Reach(
            ident="RCH-014",
            name="Upper Range",
            line=Reachline.parse("200+00", "203+00"),
            template=a_reach().template,
            method=Method.SURVEY,
            group="base",
        ),
    )
    gathered = by_group(open_book, SILT)
    assert set(gathered) == {"base"}


def test_a_reach_that_cannot_be_measured_is_left_out_not_zeroed(
    open_book: sqlite3.Connection,
) -> None:
    assert by_group(open_book, SILT) == {}


def test_the_unmeasured_reaches_come_back_with_a_reason(
    open_book: sqlite3.Connection,
) -> None:
    found = unmeasured(open_book, SILT)
    assert found[0][0] == "RCH-012"
    assert "survey" in found[0][1]


def test_a_measured_reach_is_not_in_the_unmeasured_list(
    open_book: sqlite3.Connection,
) -> None:
    load_surveys(open_book)
    assert unmeasured(open_book, SILT) == ()


def test_the_book_knows_the_day_it_is_measured_through(
    open_book: sqlite3.Connection,
) -> None:
    assert measured_through(open_book) is None
    load_surveys(open_book)
    assert measured_through(open_book) == AFTER_DAY


def test_trips_count_towards_the_day_measured_through(
    open_book: sqlite3.Connection,
) -> None:
    load_scows(open_book)
    assert measured_through(open_book) == AFTER_DAY


def test_a_zero_quantity_is_still_a_quantity(open_book: sqlite3.Connection) -> None:
    load_surveys(open_book, before=42.0, after=42.0)
    gathered = by_group(open_book, SILT)
    assert gathered["base"] == Yards.zero()
