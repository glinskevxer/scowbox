"""Cubic yards, and the one place feet turn into them."""

from __future__ import annotations

import pytest

from scowbox.errors import FieldError
from scowbox.units.volume import Yards, total


def test_cubic_feet_convert_at_twenty_seven() -> None:
    assert Yards.of_cubic_feet(27).yards == 1.0
    assert Yards.of_cubic_feet(270).yards == 10.0


def test_yards_convert_back_to_cubic_feet() -> None:
    assert Yards.of_yards(10).cubic_feet == 270.0


def test_addition_and_subtraction_stay_exact() -> None:
    a = Yards.of_yards(1200.25)
    b = Yards.of_yards(300.75)
    assert (a + b).yards == 1501.0
    assert (a - b).yards == 899.5


def test_a_long_sum_does_not_drift() -> None:
    running = Yards.zero()
    for _ in range(1000):
        running = running + Yards.of_yards(0.01)
    assert running == Yards.of_yards(10)


def test_total_matches_repeated_addition() -> None:
    parts = [Yards.of_yards(v) for v in (11.11, 22.22, 33.33)]
    assert total(parts) == Yards.of_yards(66.66)


def test_scaling_applies_a_bulking_factor() -> None:
    assert Yards.of_yards(1000).scaled(1.2) == Yards.of_yards(1200)
    assert Yards.of_yards(1000).scaled(0.0) == Yards.zero()


def test_scaling_refuses_a_negative_factor() -> None:
    with pytest.raises(FieldError):
        Yards.of_yards(100).scaled(-1)


def test_clipping_drops_a_section_that_filled_in() -> None:
    assert Yards.of_yards(-40).clipped() == Yards.zero()
    assert Yards.of_yards(40).clipped() == Yards.of_yards(40)


def test_negation_is_available_for_a_credit() -> None:
    assert (-Yards.of_yards(40)).yards == -40.0


def test_text_carries_thousands_and_two_places() -> None:
    assert str(Yards.of_yards(12345.6)) == "12,345.60 cy"


def test_rounded_is_what_a_pay_line_prints() -> None:
    assert Yards.of_yards(12345.6).rounded() == "12,346 cy"
    assert Yards.of_yards(12345.4).rounded() == "12,345 cy"


def test_volumes_order_by_size() -> None:
    assert Yards.of_yards(10) < Yards.of_yards(11)
    assert max(Yards.of_yards(10), Yards.of_yards(11)) == Yards.of_yards(11)
