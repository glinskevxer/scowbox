"""Method precedence, the tolerance and what happens outside it."""

from __future__ import annotations

import pytest

from scowbox.boxmeasure.box import BoxMeasure
from scowbox.boxmeasure.bulking import Bulking
from scowbox.errors import RuleError
from scowbox.measure.fromscow import ScowQuantity
from scowbox.measure.fromsurvey import SurveyQuantity
from scowbox.measure.governing import Governs, determine, spread_between
from scowbox.model.channel import Method, Reach, Template
from scowbox.section.volume import ReachVolume, Slice
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline, Station
from scowbox.units.volume import Yards


def survey(pay: float) -> SurveyQuantity:
    """A survey quantity whose pay volume is exactly what the test asked for."""
    volume = ReachVolume(
        "RCH-012",
        (
            Slice(
                begin=Station.parse("100+00"),
                end=Station.parse("101+00"),
                removed=Yards.of_yards(pay),
                pay=Yards.of_yards(pay),
            ),
        ),
    )
    return SurveyQuantity(
        reach="RCH-012",
        before="SV-0031",
        after="SV-0032",
        volume=volume,
        areas=(),
        unpaired=(),
        stray_before=0,
        stray_after=0,
    )


def scow(pay: float) -> ScowQuantity:
    """A scow quantity that bulks one to one and deducts nothing."""
    return ScowQuantity(
        reach="RCH-012",
        bulking=Bulking("sand", 1.0),
        deduction=0.0,
        measures=(
            BoxMeasure(
                trip="TR-04188",
                scow="SC-004",
                mean_material=8.0,
                scow_yards=Yards.of_yards(pay),
                share_full=0.5,
                trim=0.0,
                heel=0.0,
                suspect=(),
            ),
        ),
        unmeasured=(),
        suspect=(),
    )


def a_reach(method: Method) -> Reach:
    return Reach(
        ident="RCH-012",
        name="Lower Range",
        line=Reachline.parse("100+00", "140+00"),
        template=Template(bottom_width=400, authorized_depth=Depth.of_feet(42), side_slope=3),
        method=method,
        group="base",
    )


def test_spread_is_a_share_of_the_larger() -> None:
    assert spread_between(Yards.of_yards(100), Yards.of_yards(90)) == 0.1
    assert spread_between(Yards.of_yards(90), Yards.of_yards(100)) == 0.1


def test_two_nothings_are_not_apart() -> None:
    assert spread_between(Yards.zero(), Yards.zero()) == 0.0


def test_a_survey_reach_bills_the_survey() -> None:
    got = determine(a_reach(Method.SURVEY), survey(10000))
    assert got.quantity == Yards.of_yards(10000)
    assert got.governs is Governs.SURVEY
    assert not got.reconcile


def test_a_survey_reach_with_no_survey_is_refused() -> None:
    with pytest.raises(RuleError, match="has no survey quantity"):
        determine(a_reach(Method.SURVEY))


def test_a_scow_measure_on_a_survey_reach_is_kept_but_not_billed() -> None:
    got = determine(a_reach(Method.SURVEY), survey(10000), scow(4000))
    assert got.quantity == Yards.of_yards(10000)
    assert got.scow == Yards.of_yards(4000)
    assert "not billed" in got.notes[0]


def test_a_scow_reach_bills_the_scows() -> None:
    got = determine(a_reach(Method.SCOW), None, scow(9000))
    assert got.quantity == Yards.of_yards(9000)
    assert got.governs is Governs.SCOW


def test_a_scow_reach_with_no_scows_is_refused() -> None:
    with pytest.raises(RuleError, match="has no scow quantity"):
        determine(a_reach(Method.SCOW))


def test_both_agreeing_inside_the_tolerance_bills_the_survey() -> None:
    got = determine(a_reach(Method.BOTH), survey(10000), scow(9500))
    assert got.quantity == Yards.of_yards(10000)
    assert got.governs is Governs.SURVEY
    assert got.spread == 0.05
    assert not got.reconcile


def test_exactly_at_the_tolerance_still_agrees() -> None:
    got = determine(a_reach(Method.BOTH), survey(10000), scow(9000))
    assert got.governs is Governs.SURVEY
    assert not got.reconcile


def test_past_the_tolerance_bills_the_lesser_and_flags_it() -> None:
    got = determine(a_reach(Method.BOTH), survey(10000), scow(8000))
    assert got.quantity == Yards.of_yards(8000)
    assert got.governs is Governs.LESSER
    assert got.reconcile
    assert "past the 10% tolerance" in got.notes[0]


def test_the_lesser_can_be_the_survey() -> None:
    got = determine(a_reach(Method.BOTH), survey(8000), scow(10000))
    assert got.quantity == Yards.of_yards(8000)
    assert got.governs is Governs.LESSER


def test_a_wider_tolerance_lets_a_pair_agree() -> None:
    got = determine(
        a_reach(Method.BOTH),
        survey(10000),
        scow(8000),
        tolerance=0.25,
    )
    assert got.governs is Governs.SURVEY
    assert not got.reconcile


def test_a_both_reach_missing_one_side_is_refused() -> None:
    with pytest.raises(RuleError, match="missing the scow quantity"):
        determine(a_reach(Method.BOTH), survey(10000))
    with pytest.raises(RuleError, match="missing the survey quantity"):
        determine(a_reach(Method.BOTH), None, scow(10000))


def test_the_difference_is_survey_less_scow() -> None:
    got = determine(a_reach(Method.BOTH), survey(10000), scow(8000))
    assert got.difference == Yards.of_yards(2000)


def test_a_single_sided_reach_has_no_difference() -> None:
    got = determine(a_reach(Method.SURVEY), survey(10000))
    assert got.difference is None
    assert got.spread is None
