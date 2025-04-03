"""Bulking factors and the range a factor has to sit in."""

from __future__ import annotations

import pytest

from scowbox.boxmeasure.bulking import MAX_FACTOR, Bulking, materials, typical
from scowbox.errors import MissingError, RangeError
from scowbox.units.volume import Yards


def test_scow_yards_come_back_smaller_in_place() -> None:
    assert Bulking("silt", 1.2).in_place(Yards.of_yards(1200)) == Yards.of_yards(1000)


def test_bed_yards_take_more_room_in_a_scow() -> None:
    assert Bulking("silt", 1.2).in_scow(Yards.of_yards(1000)) == Yards.of_yards(1200)


def test_the_two_directions_undo_each_other() -> None:
    factor = Bulking("clay", 1.45)
    there = factor.in_scow(Yards.of_yards(1000))
    assert factor.in_place(there).yards == pytest.approx(1000, abs=0.01)


def test_a_factor_of_one_changes_nothing() -> None:
    assert Bulking("rock spoil", 1.0).in_place(Yards.of_yards(500)) == Yards.of_yards(500)


@pytest.mark.parametrize("factor", [0.9, 0.0, 2.5, -1.2])
def test_a_factor_outside_the_range_is_a_typing_error(factor: float) -> None:
    with pytest.raises(RangeError):
        Bulking("silt", factor)


def test_the_top_of_the_range_is_allowed() -> None:
    assert Bulking("stiff clay", MAX_FACTOR).factor == MAX_FACTOR


def test_the_typical_factors_cover_the_usual_materials() -> None:
    assert set(materials()) == {"sand", "silt", "clay", "mixed"}
    assert typical("silt").factor == 1.20


def test_the_typical_factors_rise_with_stiffness() -> None:
    assert typical("sand").factor < typical("silt").factor < typical("clay").factor


def test_a_material_nobody_has_a_factor_for_is_missing() -> None:
    with pytest.raises(MissingError):
        typical("shell hash")
