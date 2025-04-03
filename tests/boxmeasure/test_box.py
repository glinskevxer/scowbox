"""Box measure, and the two things that make one worthless."""

from __future__ import annotations

import datetime as dt

import pytest

from scowbox.boxmeasure.box import measure
from scowbox.errors import FieldError, RuleError
from scowbox.model.scow import BoxReading, Corner, Scow, ScowTrip

DAY = dt.date(2025, 4, 2)
SCOW = Scow("SC-004", "Dixie 41", inside_length=180, inside_width=42, inside_depth=14)


def a_trip(*, light: float = 12.0, loaded: dict[Corner, float] | None = None) -> ScowTrip:
    depths = loaded or dict.fromkeys(Corner, 4.0)
    return ScowTrip(
        ident="TR-04188",
        scow="SC-004",
        reach="RCH-012",
        loaded_on=DAY,
        placement="PA-002",
        readings=tuple(BoxReading(corner, light, depths[corner]) for corner in Corner),
    )


def test_a_level_load_measures_the_box() -> None:
    got = measure(SCOW, a_trip())
    assert got.mean_material == 8.0
    assert got.scow_yards.yards == pytest.approx(180 * 42 * 8 / 27, abs=0.01)


def test_the_share_full_is_against_the_inside_depth() -> None:
    assert measure(SCOW, a_trip()).share_full == pytest.approx(8 / 14, abs=0.001)


def test_a_level_load_has_no_trim_and_no_heel() -> None:
    got = measure(SCOW, a_trip())
    assert got.trim == 0.0
    assert got.heel == 0.0
    assert got.sound


def test_trim_is_bow_less_stern() -> None:
    heavy_bow = {
        Corner.PORT_BOW: 3.0,
        Corner.STARBOARD_BOW: 3.0,
        Corner.PORT_STERN: 5.0,
        Corner.STARBOARD_STERN: 5.0,
    }
    got = measure(SCOW, a_trip(loaded=heavy_bow))
    assert got.trim == 2.0
    assert got.mean_material == 8.0


def test_trim_past_the_tolerance_is_called_out() -> None:
    wedge = {
        Corner.PORT_BOW: 1.0,
        Corner.STARBOARD_BOW: 1.0,
        Corner.PORT_STERN: 7.0,
        Corner.STARBOARD_STERN: 7.0,
    }
    got = measure(SCOW, a_trip(loaded=wedge))
    assert not got.sound
    assert got.suspect[0].startswith("trim +6.00")


def test_heel_is_port_less_starboard() -> None:
    listed = {
        Corner.PORT_BOW: 2.0,
        Corner.PORT_STERN: 2.0,
        Corner.STARBOARD_BOW: 6.0,
        Corner.STARBOARD_STERN: 6.0,
    }
    got = measure(SCOW, a_trip(loaded=listed))
    assert got.heel == 4.0
    assert "heel +4.00 ft" in got.suspect


def test_an_empty_scow_is_called_out() -> None:
    got = measure(SCOW, a_trip(loaded=dict.fromkeys(Corner, 12.0)))
    assert got.mean_material == 0.0
    assert "no material measured" in got.suspect


def test_a_light_reading_past_the_box_depth_is_refused() -> None:
    with pytest.raises(RuleError, match="past the 14 ft inside depth"):
        measure(SCOW, a_trip(light=16.0))


def test_a_trip_carried_by_another_scow_is_refused() -> None:
    other = Scow("SC-009", "Dixie 55", inside_length=180, inside_width=42, inside_depth=14)
    with pytest.raises(FieldError):
        measure(other, a_trip())


def test_a_trip_with_no_readings_cannot_be_measured() -> None:
    plain = ScowTrip(
        ident="TR-04188",
        scow="SC-004",
        reach="RCH-012",
        loaded_on=DAY,
        placement="PA-002",
    )
    with pytest.raises(RuleError, match="no box readings"):
        measure(SCOW, plain)


def test_the_measure_names_the_trip_and_the_scow() -> None:
    got = measure(SCOW, a_trip())
    assert (got.trip, got.scow) == ("TR-04188", "SC-004")
