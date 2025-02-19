"""Average end area, and the two rules that travel with it."""

from __future__ import annotations

import pytest

from scowbox.errors import FieldError, RuleError
from scowbox.section.area import SectionArea
from scowbox.section.volume import between, reach_volume
from scowbox.units.station import Station
from scowbox.units.volume import Yards


def an_area(station: str, removed: float, pay: float | None = None) -> SectionArea:
    return SectionArea(
        station=Station.parse(station),
        removed=removed,
        pay=removed if pay is None else pay,
        left=-300,
        right=300,
    )


def test_equal_end_areas_give_a_prismatic_volume() -> None:
    slice_ = between(an_area("100+00", 270), an_area("101+00", 270))
    assert slice_.removed == Yards.of_yards(1000)
    assert slice_.length == 100.0


def test_unequal_end_areas_average() -> None:
    slice_ = between(an_area("100+00", 270), an_area("101+00", 540))
    assert slice_.removed == Yards.of_yards(1500)


def test_pay_and_removed_are_carried_separately() -> None:
    slice_ = between(an_area("100+00", 540, pay=270), an_area("101+00", 540, pay=270))
    assert slice_.removed == Yards.of_yards(2000)
    assert slice_.pay == Yards.of_yards(1000)
    assert slice_.overcut == Yards.of_yards(1000)


def test_a_section_pair_out_of_order_is_refused() -> None:
    with pytest.raises(FieldError):
        between(an_area("101+00", 270), an_area("100+00", 270))


def test_a_repeated_station_is_refused() -> None:
    with pytest.raises(FieldError):
        between(an_area("100+00", 270), an_area("100+00", 270))


def test_sections_too_far_apart_are_refused() -> None:
    with pytest.raises(RuleError) as caught:
        between(an_area("100+00", 270), an_area("104+00", 270))
    assert "400 ft apart" in str(caught.value)


def test_a_reach_sums_its_slices() -> None:
    volume = reach_volume(
        "RCH-012",
        [an_area("100+00", 270), an_area("101+00", 270), an_area("102+00", 270)],
    )
    assert volume.removed == Yards.of_yards(2000)
    assert volume.length == 200.0
    assert len(volume.slices) == 2


def test_a_reach_sorts_its_sections_before_walking_them() -> None:
    forward = reach_volume(
        "RCH-012", [an_area("100+00", 270), an_area("101+00", 540), an_area("102+00", 270)]
    )
    shuffled = reach_volume(
        "RCH-012", [an_area("102+00", 270), an_area("100+00", 270), an_area("101+00", 540)]
    )
    assert forward.removed == shuffled.removed


def test_a_reach_totals_overcut_from_its_slices() -> None:
    volume = reach_volume(
        "RCH-012",
        [an_area("100+00", 540, pay=270), an_area("101+00", 540, pay=270)],
    )
    assert volume.overcut == Yards.of_yards(1000)


def test_one_section_is_not_a_volume() -> None:
    with pytest.raises(FieldError):
        reach_volume("RCH-012", [an_area("100+00", 270)])


def test_a_reach_volume_needs_a_reach_identifier() -> None:
    with pytest.raises(FieldError):
        reach_volume("SV-0031", [an_area("100+00", 270), an_area("101+00", 270)])


def test_a_short_last_interval_contributes_its_own_length() -> None:
    volume = reach_volume(
        "RCH-012",
        [an_area("100+00", 270), an_area("101+00", 270), an_area("101+50", 270)],
    )
    assert volume.length == 150.0
    assert volume.removed == Yards.of_yards(1500)
