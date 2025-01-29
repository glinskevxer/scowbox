"""Templates, the three depths that come off them, and reach validation."""

from __future__ import annotations

import pytest

from scowbox.errors import FieldError, RangeError
from scowbox.model.channel import Method, Reach, Template
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline


def a_template(**over: float) -> Template:
    fields: dict[str, float] = {
        "bottom_width": 400.0,
        "side_slope": 3.0,
        "advance_maintenance": 2.0,
        "overdepth": 2.0,
    }
    fields.update(over)
    return Template(
        bottom_width=fields["bottom_width"],
        authorized_depth=Depth.of_feet(42),
        side_slope=fields["side_slope"],
        advance_maintenance=fields["advance_maintenance"],
        overdepth=fields["overdepth"],
    )


def a_reach(**over: object) -> Reach:
    fields: dict[str, object] = {
        "ident": "RCH-012",
        "name": "Lower Range",
        "line": Reachline.parse("100+00", "140+00"),
        "template": a_template(),
        "method": Method.SURVEY,
        "group": "base",
    }
    fields.update(over)
    return Reach(**fields)  # type: ignore[arg-type]


def test_the_three_depths_stack_in_order() -> None:
    template = a_template()
    assert template.authorized_depth == Depth.of_feet(42)
    assert template.required_depth == Depth.of_feet(44)
    assert template.pay_depth == Depth.of_feet(46)


def test_no_advance_and_no_overdepth_collapses_the_three() -> None:
    template = a_template(advance_maintenance=0, overdepth=0)
    assert template.required_depth == template.authorized_depth
    assert template.pay_depth == template.authorized_depth


def test_top_width_lays_the_slope_back_from_the_pay_depth() -> None:
    assert a_template().top_width == 400 + 2 * 3 * 46


def test_a_vertical_side_is_allowed() -> None:
    assert a_template(side_slope=0).top_width == 400.0


def test_a_template_needs_a_bottom() -> None:
    with pytest.raises(FieldError):
        a_template(bottom_width=0)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("side_slope", 11.0),
        ("side_slope", -1.0),
        ("advance_maintenance", 5.0),
        ("overdepth", 5.0),
        ("overdepth", -0.5),
    ],
)
def test_a_template_field_outside_its_range_is_refused(field: str, value: float) -> None:
    with pytest.raises(RangeError) as caught:
        a_template(**{field: value})
    assert caught.value.field == field


def test_describe_reads_as_a_drawing_note() -> None:
    assert a_template().describe() == (
        "400 ft bottom, 44.00 ft required plus 2 ft overdepth, 3:1 side slope"
    )


def test_method_says_which_measurements_a_reach_takes() -> None:
    taken = {m: (m.takes_survey, m.takes_scow) for m in Method}
    assert taken[Method.SURVEY] == (True, False)
    assert taken[Method.SCOW] == (False, True)
    assert taken[Method.BOTH] == (True, True)


def test_a_reach_carries_its_length() -> None:
    assert a_reach().length == 4000.0


def test_a_reach_needs_a_reach_identifier() -> None:
    with pytest.raises(FieldError) as caught:
        a_reach(ident="SV-0012")
    assert caught.value.field == "ident"


def test_a_reach_needs_a_name_and_a_group() -> None:
    with pytest.raises(FieldError):
        a_reach(name="  ")
    with pytest.raises(FieldError):
        a_reach(group="")


def test_reaches_that_meet_end_to_end_adjoin_either_way() -> None:
    lower = a_reach(ident="RCH-012", line=Reachline.parse("100+00", "140+00"))
    upper = a_reach(ident="RCH-013", line=Reachline.parse("140+00", "180+00"))
    assert lower.adjoins(upper)
    assert upper.adjoins(lower)


def test_reaches_with_a_gap_do_not_adjoin() -> None:
    lower = a_reach(ident="RCH-012", line=Reachline.parse("100+00", "140+00"))
    away = a_reach(ident="RCH-014", line=Reachline.parse("200+00", "240+00"))
    assert not lower.adjoins(away)


def test_reach_describe_names_the_run_and_the_cut() -> None:
    text = a_reach().describe()
    assert text.startswith("RCH-012 Lower Range, 100+00 to 140+00,")
