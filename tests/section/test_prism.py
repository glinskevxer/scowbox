"""The design surface, and what the overdepth does to the toe of slope."""

from __future__ import annotations

import pytest

from scowbox.errors import FieldError, MissingError
from scowbox.model.channel import Template
from scowbox.section.prism import Cut, Prism
from scowbox.units.depth import Depth, Elevation

DATUM = Elevation.of_feet(0)


def a_template(**over: float) -> Template:
    return Template(
        bottom_width=over.get("bottom_width", 400.0),
        authorized_depth=Depth.of_feet(over.get("authorized", 42.0)),
        side_slope=over.get("side_slope", 3.0),
        advance_maintenance=over.get("advance", 2.0),
        overdepth=over.get("overdepth", 2.0),
    )


def test_the_three_cuts_come_off_the_three_depths() -> None:
    template = a_template()
    assert Prism.of_template(template, Cut.AUTHORIZED).depth == Depth.of_feet(42)
    assert Prism.of_template(template, Cut.REQUIRED).depth == Depth.of_feet(44)
    assert Prism.of_template(template, Cut.PAY).depth == Depth.of_feet(46)


def test_the_bottom_is_centred_on_the_centreline() -> None:
    prism = Prism.of_template(a_template(), Cut.PAY)
    assert prism.left_toe == -200
    assert prism.right_toe == 200
    assert prism.on_bottom(0)
    assert prism.on_bottom(200)
    assert not prism.on_bottom(201)


def test_an_offset_centreline_moves_the_whole_cut() -> None:
    prism = Prism.of_template(a_template(), Cut.PAY, centre=50)
    assert prism.left_toe == -150
    assert prism.right_toe == 250


def test_on_the_flat_the_design_is_the_bottom() -> None:
    prism = Prism.of_template(a_template(), Cut.PAY)
    assert prism.design_elevation(0, DATUM) == Elevation.of_feet(-46)
    assert prism.design_elevation(-200, DATUM) == Elevation.of_feet(-46)


def test_beyond_the_flat_the_design_climbs_at_the_slope() -> None:
    prism = Prism.of_template(a_template(), Cut.PAY)
    assert prism.design_elevation(203, DATUM) == Elevation.of_feet(-45)
    assert prism.design_elevation(-206, DATUM) == Elevation.of_feet(-44)


def test_above_the_top_of_slope_there_is_no_prism() -> None:
    prism = Prism.of_template(a_template(), Cut.PAY)
    with pytest.raises(MissingError):
        prism.design_elevation(400, DATUM)


def test_a_vertical_side_has_no_slope_to_climb() -> None:
    prism = Prism.of_template(a_template(side_slope=0), Cut.PAY)
    assert prism.design_elevation(200, DATUM) == Elevation.of_feet(-46)
    with pytest.raises(MissingError):
        prism.design_elevation(201, DATUM)


def test_the_toe_of_slope_steps_out_as_the_cut_goes_down() -> None:
    template = a_template()
    required = Prism.of_template(template, Cut.REQUIRED)
    pay = Prism.of_template(template, Cut.PAY)
    assert required.top_half_width(DATUM) == 200 + 3 * 44
    assert pay.top_half_width(DATUM) == 200 + 3 * 46


def test_a_vertical_side_does_not_step_out() -> None:
    prism = Prism.of_template(a_template(side_slope=0), Cut.PAY)
    assert prism.top_half_width(DATUM) == 200


def test_a_top_below_the_bottom_is_refused() -> None:
    prism = Prism.of_template(a_template(), Cut.PAY)
    with pytest.raises(FieldError):
        prism.top_half_width(Elevation.of_feet(-60))


def test_lowering_carries_the_sides_down_with_the_bottom() -> None:
    prism = Prism.of_template(a_template(overdepth=0), Cut.PAY)
    lower = prism.lowered(2)
    assert lower.depth == Depth.of_feet(46)
    assert lower.top_half_width(DATUM) - prism.top_half_width(DATUM) == 6.0


def test_area_is_the_trapezoid_the_template_draws() -> None:
    prism = Prism(bottom_width=400, side_slope=3, depth=Depth.of_feet(10))
    assert prism.area_to(DATUM) == 400 * 10 + 3 * 100


def test_a_vertical_walled_cut_is_a_rectangle() -> None:
    prism = Prism(bottom_width=400, side_slope=0, depth=Depth.of_feet(10))
    assert prism.area_to(DATUM) == 4000.0


def test_a_top_at_or_below_the_bottom_encloses_nothing() -> None:
    prism = Prism(bottom_width=400, side_slope=3, depth=Depth.of_feet(10))
    assert prism.area_to(Elevation.of_feet(-10)) == 0.0
    assert prism.area_to(Elevation.of_feet(-12)) == 0.0
