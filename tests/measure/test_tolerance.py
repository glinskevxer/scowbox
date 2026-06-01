"""What would have to move for a reach to agree with itself."""

from __future__ import annotations

import pytest

from scowbox.boxmeasure.bulking import Bulking
from scowbox.errors import RuleError
from scowbox.measure.governing import Determination, Governs
from scowbox.measure.tolerance import sensitivity
from scowbox.model.channel import Method
from scowbox.units.volume import Yards

SILT = Bulking("silt", 1.20)


def a_determination(survey: float | None, scow: float | None) -> Determination:
    return Determination(
        reach="RCH-012",
        method=Method.BOTH,
        survey=None if survey is None else Yards.of_yards(survey),
        scow=None if scow is None else Yards.of_yards(scow),
        quantity=Yards.of_yards(survey or 0),
        governs=Governs.SURVEY,
        spread=None,
        reconcile=False,
        notes=(),
    )


def test_the_spread_is_the_tolerance_that_would_admit_the_pair() -> None:
    found = sensitivity(a_determination(10000, 8000), SILT)
    assert found.spread == 0.2


def test_the_difference_is_survey_less_scow() -> None:
    found = sensitivity(a_determination(10000, 8000), SILT)
    assert found.difference == Yards.of_yards(2000)


def test_the_factor_that_would_match_is_scaled_by_the_ratio() -> None:
    found = sensitivity(a_determination(10000, 8000), SILT)
    assert found.factor == pytest.approx(0.96, abs=0.001)


def test_scows_short_of_the_survey_want_a_smaller_factor() -> None:
    short = sensitivity(a_determination(10000, 8000), SILT)
    long = sensitivity(a_determination(8000, 10000), SILT)
    assert short.factor is not None
    assert long.factor is not None
    assert short.factor < SILT.factor < long.factor


def test_a_factor_a_soil_could_not_have_is_not_credible() -> None:
    found = sensitivity(a_determination(10000, 8000), SILT)
    assert not found.credible


def test_a_factor_inside_the_range_is_credible() -> None:
    found = sensitivity(a_determination(10000, 11000), SILT)
    assert found.credible


def test_a_deduction_can_bring_the_scows_down() -> None:
    found = sensitivity(a_determination(8000, 10000), SILT)
    assert found.deduction == 0.2


def test_a_deduction_cannot_close_a_gap_the_other_way() -> None:
    found = sensitivity(a_determination(10000, 8000), SILT)
    assert found.deduction is None


def test_a_side_that_measured_nothing_has_no_factor() -> None:
    found = sensitivity(a_determination(10000, 0), SILT)
    assert found.factor is None
    assert found.deduction is None


def test_a_reach_measured_one_way_has_nothing_to_move() -> None:
    with pytest.raises(RuleError, match="not measured both ways"):
        sensitivity(a_determination(10000, None), SILT)


def test_it_describes_itself_in_one_line() -> None:
    found = sensitivity(a_determination(10000, 8000), SILT)
    assert found.describe() == ("RCH-012: survey 10,000 cy, scow 8,000 cy, 20.0% apart")
