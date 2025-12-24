"""Shoaling: the same sections, paired the other way round."""

from __future__ import annotations

import datetime as dt

import pytest

from scowbox.datum.tide import TideReading, TideRecord
from scowbox.errors import FieldError, RuleError
from scowbox.measure.shoaling import shoaling
from scowbox.model.channel import Method, Reach, Template
from scowbox.model.survey import Sounding, Survey, SurveyKind
from scowbox.units.clock import moment
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline, Station

FIRST = dt.date(2025, 1, 6)
SECOND = dt.date(2026, 1, 6)
STATIONS = ["100+00", "101+00", "102+00", "103+00"]


def a_reach() -> Reach:
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
        method=Method.SURVEY,
        group="base",
    )


def a_survey(ident: str, day: dt.date, depth: float, stations: list[str] | None = None) -> Survey:
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
            for station in (stations or STATIONS)
            for offset in (-300.0, 0.0, 300.0)
        ),
    )


def a_tide(day: dt.date) -> TideRecord:
    return TideRecord(
        "8658120",
        (TideReading(moment(day, "06:54"), 2.0), TideReading(moment(day, "07:06"), 2.0)),
    )


def test_a_bed_that_rose_gained_the_volume() -> None:
    got = shoaling(
        a_reach(),
        a_survey("SV-0032", FIRST, 46.0),
        a_survey("SV-0040", SECOND, 44.0),
        a_tide(FIRST),
        a_tide(SECOND),
    )
    assert got.filling
    assert got.gained.yards == pytest.approx(2 * 600 * 300 / 27, abs=0.05)


def test_the_rate_is_over_the_days_between_the_two() -> None:
    got = shoaling(
        a_reach(),
        a_survey("SV-0032", FIRST, 46.0),
        a_survey("SV-0040", SECOND, 44.0),
        a_tide(FIRST),
        a_tide(SECOND),
    )
    assert got.days == 365
    assert got.yards_a_day == pytest.approx(got.gained.yards / 365, abs=0.01)
    assert got.yards_a_year == pytest.approx(got.gained.yards * 365.25 / 365, abs=1.0)


def test_a_reach_that_scoured_gained_nothing() -> None:
    got = shoaling(
        a_reach(),
        a_survey("SV-0032", FIRST, 44.0),
        a_survey("SV-0040", SECOND, 46.0),
        a_tide(FIRST),
        a_tide(SECOND),
    )
    assert not got.filling
    assert got.gained.hundredths == 0


def test_material_above_the_prism_still_counts() -> None:
    got = shoaling(
        a_reach(),
        a_survey("SV-0032", FIRST, 40.0),
        a_survey("SV-0040", SECOND, 30.0),
        a_tide(FIRST),
        a_tide(SECOND),
    )
    assert got.gained.yards == pytest.approx(10 * 600 * 300 / 27, abs=0.1)


def test_the_sections_are_counted() -> None:
    got = shoaling(
        a_reach(),
        a_survey("SV-0032", FIRST, 46.0),
        a_survey("SV-0040", SECOND, 44.0),
        a_tide(FIRST),
        a_tide(SECOND),
    )
    assert got.sections == 4
    assert got.unpaired == ()


def test_a_station_only_one_survey_reached_is_left_out() -> None:
    got = shoaling(
        a_reach(),
        a_survey("SV-0032", FIRST, 46.0),
        a_survey("SV-0040", SECOND, 44.0, STATIONS[:3]),
        a_tide(FIRST),
        a_tide(SECOND),
    )
    assert got.unpaired == (Station.parse("103+00"),)


def test_two_surveys_too_close_together_are_not_a_rate() -> None:
    close = dt.date(2025, 1, 20)
    with pytest.raises(RuleError, match="14 days apart"):
        shoaling(
            a_reach(),
            a_survey("SV-0032", FIRST, 46.0),
            a_survey("SV-0040", close, 44.0),
            a_tide(FIRST),
            a_tide(close),
        )


def test_a_shorter_floor_can_be_asked_for() -> None:
    close = dt.date(2025, 1, 20)
    got = shoaling(
        a_reach(),
        a_survey("SV-0032", FIRST, 46.0),
        a_survey("SV-0040", close, 44.0),
        a_tide(FIRST),
        a_tide(close),
        min_days=7,
    )
    assert got.days == 14


def test_the_later_survey_has_to_be_later() -> None:
    with pytest.raises(RuleError, match="not run after"):
        shoaling(
            a_reach(),
            a_survey("SV-0040", SECOND, 44.0),
            a_survey("SV-0032", FIRST, 46.0),
            a_tide(SECOND),
            a_tide(FIRST),
        )


def test_a_survey_of_another_reach_is_refused() -> None:
    stray = Survey(
        ident="SV-0099",
        reach="RCH-014",
        kind=SurveyKind.AFTER,
        taken_on=SECOND,
        vessel="Cape Fear",
        transducer_draft=2.0,
        gauge="8658120",
    )
    with pytest.raises(FieldError):
        shoaling(a_reach(), a_survey("SV-0032", FIRST, 46.0), stray, a_tide(FIRST), a_tide(SECOND))
