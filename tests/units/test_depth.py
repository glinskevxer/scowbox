"""Depth counts downward, elevation counts upward, and the two do not mix."""

from __future__ import annotations

import pytest

from scowbox.errors import FieldError, RangeError
from scowbox.units.depth import Depth, Elevation, parse_depth


def test_a_depth_is_positive_downward() -> None:
    assert Depth.of_feet(42).feet == 42.0
    assert str(Depth.of_feet(42.5)) == "42.50 ft"


def test_an_elevation_is_positive_upward_and_prints_its_sign() -> None:
    assert str(Elevation.of_feet(-38.6)) == "-38.60 ft"
    assert str(Elevation.of_feet(1.2)) == "+1.20 ft"


def test_depth_and_elevation_convert_both_ways() -> None:
    depth = Depth.of_feet(42)
    assert depth.elevation() == Elevation.of_feet(-42)
    assert depth.elevation().depth() == depth


def test_deeper_than_reads_the_way_the_word_does() -> None:
    assert Depth.of_feet(44).deeper_than(Depth.of_feet(42))
    assert not Depth.of_feet(40).deeper_than(Depth.of_feet(42))


def test_above_reads_the_way_the_word_does() -> None:
    assert Elevation.of_feet(-38).above(Elevation.of_feet(-42))
    assert not Elevation.of_feet(-44).above(Elevation.of_feet(-42))


def test_below_walks_an_overdepth_allowance_down() -> None:
    required = Depth.of_feet(42)
    assert required.below(2).feet == 44.0
    assert required.below(0.5).feet == 42.5


def test_raised_walks_an_elevation_up() -> None:
    assert Elevation.of_feet(-38.6).raised(1.6) == Elevation.of_feet(-37.0)


def test_subtraction_gives_feet_between() -> None:
    assert Depth.of_feet(44) - Depth.of_feet(42) == 2.0
    assert Elevation.of_feet(-38) - Elevation.of_feet(-42) == 4.0


def test_a_reading_past_the_deepest_channel_is_refused() -> None:
    with pytest.raises(RangeError):
        Depth.of_feet(420)
    with pytest.raises(RangeError):
        Elevation.of_feet(-420)


def test_hundredths_do_not_drift_over_a_long_sum() -> None:
    running = Depth.of_feet(0)
    for _ in range(200):
        running = running.below(0.01)
    assert running == Depth.of_feet(2)


def test_parse_depth_takes_a_trailing_unit() -> None:
    assert parse_depth("42.5") == Depth.of_feet(42.5)
    assert parse_depth(" 42.5 ft ") == Depth.of_feet(42.5)


def test_parse_depth_refuses_a_negative_depth() -> None:
    with pytest.raises(FieldError) as caught:
        parse_depth("-42.5")
    assert "written positive" in str(caught.value)


def test_parse_depth_refuses_words() -> None:
    with pytest.raises(FieldError):
        parse_depth("deep")
