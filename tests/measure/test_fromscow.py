"""A stack of box measure sheets worked up into a reach quantity."""

from __future__ import annotations

import datetime as dt

import pytest

from scowbox.boxmeasure.bulking import Bulking
from scowbox.errors import FieldError, MissingError, RuleError
from scowbox.measure.fromscow import scow_quantity
from scowbox.model.channel import Method, Reach, Template
from scowbox.model.scow import BoxReading, Corner, Scow, ScowTrip
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline
from scowbox.units.volume import Yards

DAY = dt.date(2025, 4, 2)
SCOW = Scow("SC-004", "Dixie 41", inside_length=180, inside_width=42, inside_depth=14)
FLEET = {"SC-004": SCOW}
SILT = Bulking("silt", 1.20)
ONE_LOAD = Yards.of_cubic_feet(180 * 42 * 8)


def a_reach(method: Method = Method.SCOW) -> Reach:
    return Reach(
        ident="RCH-012",
        name="Lower Range",
        line=Reachline.parse("100+00", "140+00"),
        template=Template(bottom_width=400, authorized_depth=Depth.of_feet(42), side_slope=3),
        method=method,
        group="base",
    )


def level(loaded: float = 4.0) -> tuple[BoxReading, ...]:
    return tuple(BoxReading(corner, 12.0, loaded) for corner in Corner)


def a_trip(ident: str, readings: tuple[BoxReading, ...] = (), reach: str = "RCH-012") -> ScowTrip:
    return ScowTrip(
        ident=ident,
        scow="SC-004",
        reach=reach,
        loaded_on=DAY,
        placement="PA-002",
        readings=readings,
    )


def test_one_measured_trip_is_one_box() -> None:
    got = scow_quantity(a_reach(), FLEET, [a_trip("TR-04188", level())], SILT)
    assert got.trips == 1
    assert got.scow_yards == ONE_LOAD


def test_two_trips_add_up_to_two_boxes() -> None:
    got = scow_quantity(
        a_reach(), FLEET, [a_trip("TR-04188", level()), a_trip("TR-04190", level())], SILT
    )
    assert got.scow_yards.yards == pytest.approx(2 * ONE_LOAD.yards, abs=0.01)


def test_in_place_yards_come_back_smaller_than_scow_yards() -> None:
    got = scow_quantity(a_reach(), FLEET, [a_trip("TR-04188", level())], SILT)
    assert got.place_yards.yards == pytest.approx(ONE_LOAD.yards / 1.2, abs=0.01)


def test_with_no_deduction_everything_in_place_is_paid() -> None:
    got = scow_quantity(a_reach(), FLEET, [a_trip("TR-04188", level())], SILT)
    assert got.pay == got.place_yards
    assert got.deducted == Yards.zero()


def test_a_deduction_takes_a_share_off_the_pay() -> None:
    got = scow_quantity(a_reach(), FLEET, [a_trip("TR-04188", level())], SILT, deduction=0.15)
    assert got.pay.yards == pytest.approx(got.place_yards.yards * 0.85, abs=0.02)
    assert got.deducted.yards == pytest.approx(got.place_yards.yards * 0.15, abs=0.02)


def test_a_deduction_of_one_or_more_is_refused() -> None:
    with pytest.raises(FieldError):
        scow_quantity(a_reach(), FLEET, [], SILT, deduction=1.0)
    with pytest.raises(FieldError):
        scow_quantity(a_reach(), FLEET, [], SILT, deduction=-0.1)


def test_an_unmeasured_trip_is_counted_and_named() -> None:
    got = scow_quantity(a_reach(), FLEET, [a_trip("TR-04188", level()), a_trip("TR-04190")], SILT)
    assert got.trips == 2
    assert got.unmeasured == ("TR-04190",)
    assert got.scow_yards == ONE_LOAD


def test_a_suspect_measure_is_counted_and_named() -> None:
    wedge = (
        BoxReading(Corner.PORT_BOW, 12.0, 1.0),
        BoxReading(Corner.STARBOARD_BOW, 12.0, 1.0),
        BoxReading(Corner.PORT_STERN, 12.0, 7.0),
        BoxReading(Corner.STARBOARD_STERN, 12.0, 7.0),
    )
    got = scow_quantity(a_reach(), FLEET, [a_trip("TR-04188", wedge)], SILT)
    assert got.suspect == ("TR-04188",)
    assert got.scow_yards.hundredths > 0


def test_a_trip_from_another_reach_is_refused() -> None:
    with pytest.raises(FieldError):
        scow_quantity(a_reach(), FLEET, [a_trip("TR-04188", level(), reach="RCH-014")], SILT)


def test_a_trip_in_a_scow_nobody_has_measured_is_refused() -> None:
    with pytest.raises(MissingError):
        scow_quantity(a_reach(), {}, [a_trip("TR-04188", level())], SILT)


def test_a_survey_measured_reach_does_not_take_a_scow_quantity() -> None:
    with pytest.raises(RuleError, match="measured by survey"):
        scow_quantity(a_reach(Method.SURVEY), FLEET, [], SILT)


def test_a_reach_measured_both_ways_still_takes_scows() -> None:
    got = scow_quantity(a_reach(Method.BOTH), FLEET, [a_trip("TR-04188", level())], SILT)
    assert got.trips == 1


def test_a_stiffer_material_gives_fewer_in_place_yards() -> None:
    silt = scow_quantity(a_reach(), FLEET, [a_trip("TR-04188", level())], SILT)
    clay = scow_quantity(a_reach(), FLEET, [a_trip("TR-04188", level())], Bulking("clay", 1.45))
    assert clay.place_yards < silt.place_yards


def test_no_trips_at_all_is_no_quantity() -> None:
    got = scow_quantity(a_reach(), FLEET, [], SILT)
    assert got.trips == 0
    assert got.scow_yards == Yards.zero()
    assert got.pay == Yards.zero()
