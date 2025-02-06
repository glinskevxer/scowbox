"""Reduction to datum, one correction at a time."""

from __future__ import annotations

import datetime as dt

import pytest

from scowbox.datum.reduce import Correction, bed_elevation, reduce_one, reduce_survey
from scowbox.datum.tide import TideReading, TideRecord
from scowbox.errors import RangeError, RuleError
from scowbox.model.survey import Sounding, Survey, SurveyKind
from scowbox.units.clock import moment
from scowbox.units.depth import Depth, Elevation
from scowbox.units.station import Station

DAY = dt.date(2025, 3, 14)


def a_sounding(clock: str = "07:03", depth: float = 40.0, offset: float = 0.0) -> Sounding:
    return Sounding(
        station=Station.parse("100+00"),
        offset=offset,
        raw_depth=Depth.of_feet(depth),
        taken=moment(DAY, clock),
    )


def a_tide() -> TideRecord:
    return TideRecord(
        "8658120",
        (
            TideReading(moment(DAY, "07:00"), 1.0),
            TideReading(moment(DAY, "07:06"), 1.6),
        ),
    )


def a_survey(*soundings: Sounding, draft: float = 2.5) -> Survey:
    return Survey(
        ident="SV-0031",
        reach="RCH-012",
        kind=SurveyKind.BEFORE,
        taken_on=DAY,
        vessel="Cape Fear",
        transducer_draft=draft,
        soundings=soundings,
    )


def test_a_flat_calm_reading_is_the_tide_less_draft_less_depth() -> None:
    where = bed_elevation(Depth.of_feet(40), 1.0, Correction(draft=2.5))
    assert where == Elevation.of_feet(1.0 - 2.5 - 40.0)


def test_squat_pushes_the_head_further_under() -> None:
    still = bed_elevation(Depth.of_feet(40), 1.0, Correction(draft=2.5))
    running = bed_elevation(Depth.of_feet(40), 1.0, Correction(draft=2.5, squat=0.4))
    assert still - running == 0.4


def test_the_index_correction_lands_on_the_reading() -> None:
    plain = bed_elevation(Depth.of_feet(40), 1.0, Correction(draft=2.5))
    corrected = bed_elevation(Depth.of_feet(40), 1.0, Correction(draft=2.5, index=0.2))
    assert plain - corrected == 0.2


def test_a_negative_index_lifts_the_bed() -> None:
    corrected = bed_elevation(Depth.of_feet(40), 1.0, Correction(draft=2.5, index=-0.2))
    assert corrected == Elevation.of_feet(-41.3)


def test_a_higher_tide_puts_the_same_reading_on_a_deeper_bed() -> None:
    low = bed_elevation(Depth.of_feet(40), 1.0, Correction(draft=2.5))
    high = bed_elevation(Depth.of_feet(40), 2.0, Correction(draft=2.5))
    assert high - low == 1.0


@pytest.mark.parametrize(
    ("field", "value"),
    [("draft", 0.0), ("draft", 13.0), ("squat", 3.0), ("squat", -0.1), ("index", 1.5)],
)
def test_a_correction_outside_its_range_is_refused(field: str, value: float) -> None:
    fields = {"draft": 2.5}
    fields[field] = value
    with pytest.raises(RangeError) as caught:
        Correction(**fields)
    assert caught.value.field == field


def test_a_shot_reads_as_a_depth_as_well() -> None:
    shot = reduce_one(a_sounding(), 1.0, Correction(draft=2.5))
    assert shot.depth == Depth.of_feet(41.5)
    assert shot.station == Station.parse("100+00")


def test_reducing_a_survey_uses_the_tide_at_each_shot() -> None:
    survey = a_survey(a_sounding("07:00"), a_sounding("07:06"))
    shots = reduce_survey(survey, a_tide())
    assert shots[0].bed == Elevation.of_feet(-41.5)
    assert shots[1].bed == Elevation.of_feet(-40.9)


def test_reducing_a_survey_takes_the_draft_off_the_survey() -> None:
    shallow = reduce_survey(a_survey(a_sounding("07:00"), draft=2.5), a_tide())
    deep = reduce_survey(a_survey(a_sounding("07:00"), draft=4.5), a_tide())
    assert shallow[0].bed - deep[0].bed == 2.0


def test_reducing_a_survey_carries_squat_and_index_through() -> None:
    survey = a_survey(a_sounding("07:00"))
    shots = reduce_survey(survey, a_tide(), squat=0.4, index=0.1)
    assert shots[0].bed == Elevation.of_feet(-42.0)


def test_a_survey_the_gauge_did_not_cover_fails_loudly() -> None:
    thin = TideRecord("8658120", (TideReading(moment(DAY, "07:00"), 1.0),))
    with pytest.raises(Exception, match="tide reading"):
        reduce_survey(a_survey(a_sounding("07:03")), thin)


def test_a_gauge_gap_stops_the_whole_survey() -> None:
    gapped = TideRecord(
        "8658120",
        (TideReading(moment(DAY, "07:00"), 1.0), TideReading(moment(DAY, "09:00"), 3.0)),
    )
    with pytest.raises(RuleError):
        reduce_survey(a_survey(a_sounding("08:00")), gapped)


def test_an_empty_survey_reduces_to_nothing() -> None:
    assert reduce_survey(a_survey(), a_tide()) == ()
