"""A pair of surveys worked up into a reach quantity."""

from __future__ import annotations

import datetime as dt

import pytest

from scowbox.datum.tide import TideReading, TideRecord
from scowbox.errors import FieldError, RuleError
from scowbox.measure.fromsurvey import survey_quantity
from scowbox.model.channel import Method, Reach, Template
from scowbox.model.survey import Sounding, Survey, SurveyKind
from scowbox.units.clock import moment
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline, Station

BEFORE_DAY = dt.date(2025, 3, 14)
AFTER_DAY = dt.date(2025, 4, 18)


def a_reach(**over: object) -> Reach:
    fields: dict[str, object] = {
        "ident": "RCH-012",
        "name": "Lower Range",
        "line": Reachline.parse("100+00", "103+00"),
        "template": Template(
            bottom_width=600,
            authorized_depth=Depth.of_feet(42),
            side_slope=0,
            advance_maintenance=2,
            overdepth=2,
        ),
        "method": Method.SURVEY,
        "group": "base",
    }
    fields.update(over)
    return Reach(**fields)  # type: ignore[arg-type]


def flat_shots(day: dt.date, depth: float, stations: list[str]) -> tuple[Sounding, ...]:
    return tuple(
        Sounding(
            station=Station.parse(station),
            offset=offset,
            raw_depth=Depth.of_feet(depth),
            taken=moment(day, "07:00"),
        )
        for station in stations
        for offset in (-300.0, 0.0, 300.0)
    )


def a_survey(
    ident: str, kind: SurveyKind, day: dt.date, depth: float, stations: list[str]
) -> Survey:
    return Survey(
        ident=ident,
        reach="RCH-012",
        kind=kind,
        taken_on=day,
        vessel="Cape Fear",
        transducer_draft=2.0,
        gauge="8658120",
        soundings=flat_shots(day, depth, stations),
    )


def a_tide(day: dt.date) -> TideRecord:
    return TideRecord(
        "8658120",
        (TideReading(moment(day, "06:54"), 2.0), TideReading(moment(day, "07:06"), 2.0)),
    )


STATIONS = ["100+00", "101+00", "102+00", "103+00"]


def a_pair(before_depth: float = 38.0, after_depth: float = 42.0) -> tuple[Survey, Survey]:
    return (
        a_survey("SV-0031", SurveyKind.BEFORE, BEFORE_DAY, before_depth, STATIONS),
        a_survey("SV-0032", SurveyKind.AFTER, AFTER_DAY, after_depth, STATIONS),
    )


def test_a_flat_cut_gives_the_volume_the_arithmetic_says() -> None:
    before, after = a_pair()
    got = survey_quantity(a_reach(), before, after, a_tide(BEFORE_DAY), a_tide(AFTER_DAY))
    assert got.sections == 4
    assert got.volume.removed.yards == pytest.approx(4 * 600 * 300 / 27)
    assert got.volume.pay == got.volume.removed


def test_a_cut_below_the_prism_is_not_all_paid() -> None:
    before, after = a_pair(after_depth=48.0)
    got = survey_quantity(a_reach(), before, after, a_tide(BEFORE_DAY), a_tide(AFTER_DAY))
    assert got.volume.removed.yards == pytest.approx(10 * 600 * 300 / 27)
    assert got.volume.pay.yards == pytest.approx(8 * 600 * 300 / 27)
    assert got.volume.overcut.yards == pytest.approx(2 * 600 * 300 / 27, abs=0.05)


def test_the_quantity_names_both_surveys_and_the_reach() -> None:
    before, after = a_pair()
    got = survey_quantity(a_reach(), before, after, a_tide(BEFORE_DAY), a_tide(AFTER_DAY))
    assert (got.reach, got.before, got.after) == ("RCH-012", "SV-0031", "SV-0032")


def test_a_station_only_one_survey_reached_is_left_out_and_named() -> None:
    before = a_survey("SV-0031", SurveyKind.BEFORE, BEFORE_DAY, 38.0, STATIONS)
    after = a_survey("SV-0032", SurveyKind.AFTER, AFTER_DAY, 42.0, STATIONS[:3])
    got = survey_quantity(a_reach(), before, after, a_tide(BEFORE_DAY), a_tide(AFTER_DAY))
    assert got.unpaired == (Station.parse("103+00"),)
    assert got.sections == 3
    assert got.paired_share == 0.75


def test_shots_between_the_sections_are_counted_as_strays() -> None:
    before = a_survey("SV-0031", SurveyKind.BEFORE, BEFORE_DAY, 38.0, [*STATIONS, "100+50"])
    after = a_survey("SV-0032", SurveyKind.AFTER, AFTER_DAY, 42.0, STATIONS)
    got = survey_quantity(a_reach(), before, after, a_tide(BEFORE_DAY), a_tide(AFTER_DAY))
    assert got.stray_before == 3
    assert got.stray_after == 0


def test_too_few_paired_sections_is_not_a_volume() -> None:
    before = a_survey("SV-0031", SurveyKind.BEFORE, BEFORE_DAY, 38.0, STATIONS)
    after = a_survey("SV-0032", SurveyKind.AFTER, AFTER_DAY, 42.0, ["100+00"])
    with pytest.raises(RuleError, match="not a volume"):
        survey_quantity(a_reach(), before, after, a_tide(BEFORE_DAY), a_tide(AFTER_DAY))


def test_a_survey_of_another_reach_is_refused() -> None:
    before, after = a_pair()
    with pytest.raises(FieldError):
        survey_quantity(
            a_reach(ident="RCH-014"), before, after, a_tide(BEFORE_DAY), a_tide(AFTER_DAY)
        )


def test_the_two_surveys_have_to_be_a_before_and_an_after() -> None:
    before, after = a_pair()
    with pytest.raises(RuleError, match="not a before"):
        survey_quantity(a_reach(), after, after, a_tide(AFTER_DAY), a_tide(AFTER_DAY))
    with pytest.raises(RuleError, match="not an after"):
        survey_quantity(a_reach(), before, before, a_tide(BEFORE_DAY), a_tide(BEFORE_DAY))


def test_an_after_survey_run_first_is_refused() -> None:
    before = a_survey("SV-0031", SurveyKind.BEFORE, AFTER_DAY, 38.0, STATIONS)
    after = a_survey("SV-0032", SurveyKind.AFTER, BEFORE_DAY, 42.0, STATIONS)
    with pytest.raises(RuleError, match="before SV-0031"):
        survey_quantity(a_reach(), before, after, a_tide(AFTER_DAY), a_tide(BEFORE_DAY))


def test_a_scow_measured_reach_does_not_take_a_survey_quantity() -> None:
    before, after = a_pair()
    with pytest.raises(RuleError, match="measured by scow"):
        survey_quantity(
            a_reach(method=Method.SCOW), before, after, a_tide(BEFORE_DAY), a_tide(AFTER_DAY)
        )


def test_a_reach_measured_both_ways_still_takes_a_survey() -> None:
    before, after = a_pair()
    got = survey_quantity(
        a_reach(method=Method.BOTH), before, after, a_tide(BEFORE_DAY), a_tide(AFTER_DAY)
    )
    assert got.sections == 4


def test_a_wider_section_interval_gives_fewer_sections() -> None:
    before, after = a_pair()
    got = survey_quantity(
        a_reach(), before, after, a_tide(BEFORE_DAY), a_tide(AFTER_DAY), interval=200
    )
    assert got.sections == 3
    assert got.volume.length == 300.0


def test_an_interval_that_lands_between_the_shots_leaves_a_gap() -> None:
    before, after = a_pair()
    with pytest.raises(RuleError, match="200 ft average end area is trusted over"):
        survey_quantity(
            a_reach(), before, after, a_tide(BEFORE_DAY), a_tide(AFTER_DAY), interval=150
        )
