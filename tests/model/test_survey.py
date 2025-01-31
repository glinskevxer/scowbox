"""Survey records, and the soundings they carry uncorrected."""

from __future__ import annotations

import datetime as dt

import pytest

from scowbox.errors import FieldError, RangeError
from scowbox.model.survey import Sounding, Survey, SurveyKind
from scowbox.units.clock import moment
from scowbox.units.depth import Depth
from scowbox.units.station import Station

DAY = dt.date(2025, 3, 14)


def a_sounding(station: str = "100+00", offset: float = 0.0, depth: float = 40.0) -> Sounding:
    return Sounding(
        station=Station.parse(station),
        offset=offset,
        raw_depth=Depth.of_feet(depth),
        taken=moment(DAY, "07:45"),
    )


def a_survey(**over: object) -> Survey:
    fields: dict[str, object] = {
        "ident": "SV-0031",
        "reach": "RCH-012",
        "kind": SurveyKind.BEFORE,
        "taken_on": DAY,
        "vessel": "Cape Fear",
        "transducer_draft": 2.5,
        "soundings": (),
    }
    fields.update(over)
    return Survey(**fields)  # type: ignore[arg-type]


def test_only_a_before_and_an_after_pay() -> None:
    assert SurveyKind.BEFORE.pays
    assert SurveyKind.AFTER.pays
    assert not SurveyKind.PROGRESS.pays
    assert not SurveyKind.SWEEP.pays


def test_a_sounding_reads_below_the_transducer() -> None:
    with pytest.raises(FieldError) as caught:
        a_sounding(depth=0)
    assert caught.value.field == "raw_depth"


def test_a_sounding_far_outside_the_channel_is_refused() -> None:
    with pytest.raises(RangeError):
        a_sounding(offset=2500)


def test_a_sounding_needs_a_zoned_time() -> None:
    with pytest.raises(FieldError):
        Sounding(
            station=Station.parse("100+00"),
            offset=0,
            raw_depth=Depth.of_feet(40),
            taken=dt.datetime(2025, 3, 14, 7, 45),  # noqa: DTZ001
        )


def test_a_survey_needs_its_own_identifier_and_a_reach() -> None:
    with pytest.raises(FieldError):
        a_survey(ident="RCH-012")
    with pytest.raises(FieldError):
        a_survey(reach="SV-0031")


def test_a_survey_names_its_vessel() -> None:
    with pytest.raises(FieldError):
        a_survey(vessel=" ")


@pytest.mark.parametrize("draft", [0.0, -1.0, 14.0])
def test_a_transducer_draft_outside_the_range_is_refused(draft: float) -> None:
    with pytest.raises(RangeError):
        a_survey(transducer_draft=draft)


def test_stations_come_back_distinct_and_in_order() -> None:
    survey = a_survey(
        soundings=(
            a_sounding("101+00"),
            a_sounding("100+00", offset=-50),
            a_sounding("100+00", offset=50),
        )
    )
    assert [str(s) for s in survey.stations()] == ["100+00", "101+00"]
    assert survey.count == 3


def test_a_station_reads_left_to_right() -> None:
    survey = a_survey(
        soundings=(
            a_sounding("100+00", offset=50),
            a_sounding("100+00", offset=-50),
            a_sounding("100+00", offset=0),
        )
    )
    assert [s.offset for s in survey.at_station(Station.parse("100+00"))] == [-50, 0, 50]


def test_a_station_with_nothing_on_it_comes_back_empty() -> None:
    assert a_survey().at_station(Station.parse("100+00")) == ()


def test_with_soundings_leaves_the_original_alone() -> None:
    empty = a_survey()
    loaded = empty.with_soundings((a_sounding(),))
    assert empty.count == 0
    assert loaded.count == 1
    assert loaded.ident == empty.ident
