"""End areas: what was removed, what is inside the prism, and what is not."""

from __future__ import annotations

import pytest

from scowbox.errors import MissingError
from scowbox.section.area import section_area
from scowbox.section.bedline import Point, Profile
from scowbox.section.prism import Prism
from scowbox.units.depth import Depth, Elevation
from scowbox.units.station import Station

STATION = Station.parse("100+00")


def flat(elevation: float, left: float = -300, right: float = 300) -> Profile:
    return Profile(
        STATION,
        (Point(left, Elevation.of_feet(elevation)), Point(right, Elevation.of_feet(elevation))),
    )


def a_prism(depth: float = 46, width: float = 400, slope: float = 0.0) -> Prism:
    return Prism(bottom_width=width, side_slope=slope, depth=Depth.of_feet(depth))


def test_nothing_dug_is_nothing_removed() -> None:
    area = section_area(flat(-44), flat(-44), a_prism())
    assert area.removed == 0.0
    assert area.pay == 0.0


def test_a_flat_cut_inside_the_prism_is_all_pay() -> None:
    area = section_area(flat(-40), flat(-42), a_prism(depth=46, width=600))
    assert area.removed == pytest.approx(2 * 600)
    assert area.pay == pytest.approx(2 * 600)
    assert area.overcut == pytest.approx(0.0)


def test_a_cut_below_the_prism_pays_only_to_the_prism() -> None:
    area = section_area(flat(-40), flat(-48), a_prism(depth=46, width=600))
    assert area.removed == pytest.approx(8 * 600)
    assert area.pay == pytest.approx(6 * 600)
    assert area.overcut == pytest.approx(2 * 600)


def test_a_cut_outside_a_vertical_walled_prism_pays_nothing() -> None:
    area = section_area(flat(-40), flat(-44), a_prism(depth=46, width=200))
    assert area.removed == pytest.approx(4 * 600)
    assert area.pay == pytest.approx(4 * 200)
    assert area.overcut == pytest.approx(4 * 400)


def test_a_bed_already_below_the_prism_pays_nothing_for_what_was_there() -> None:
    area = section_area(flat(-48), flat(-50), a_prism(depth=46, width=600))
    assert area.removed == pytest.approx(2 * 600)
    assert area.pay == pytest.approx(0.0)


def test_material_that_filled_in_is_not_a_negative_quantity() -> None:
    area = section_area(flat(-44), flat(-40), a_prism(depth=46, width=600))
    assert area.removed == 0.0
    assert area.pay == 0.0


def test_a_sloping_bed_crossing_the_prism_splits_at_the_crossing() -> None:
    before = Profile(
        STATION, (Point(-100, Elevation.of_feet(-40)), Point(100, Elevation.of_feet(-40)))
    )
    after = Profile(
        STATION, (Point(-100, Elevation.of_feet(-40)), Point(100, Elevation.of_feet(-48)))
    )
    area = section_area(before, after, a_prism(depth=44, width=400))
    assert area.removed == pytest.approx(0.5 * 200 * 8)
    # Left of the crossing the cut is the floor and the wedge is a triangle.
    # Right of it the prism is the floor and the wedge is four feet deep flat.
    assert area.pay == pytest.approx(0.5 * 100 * 4 + 100 * 4)
    assert area.overcut == pytest.approx(800 - 600)


def test_the_answer_does_not_depend_on_the_shot_spacing() -> None:
    coarse_before = flat(-40, -200, 200)
    coarse_after = Profile(
        STATION, (Point(-200, Elevation.of_feet(-44)), Point(200, Elevation.of_feet(-48)))
    )
    fine_after = Profile(
        STATION,
        tuple(
            Point(float(x), Elevation.of_feet(-44 - (x + 200) / 100)) for x in range(-200, 201, 25)
        ),
    )
    coarse = section_area(coarse_before, coarse_after, a_prism(depth=46, width=600))
    fine = section_area(coarse_before, fine_after, a_prism(depth=46, width=600))
    assert coarse.pay == pytest.approx(fine.pay)
    assert coarse.removed == pytest.approx(fine.removed)


def test_a_sloped_prism_pays_out_to_its_toe_of_slope() -> None:
    area = section_area(flat(-40), flat(-46), a_prism(depth=46, width=200, slope=3))
    assert area.pay == pytest.approx(200 * 6 + 3 * 36)


def test_the_section_reports_the_offsets_it_worked_between() -> None:
    area = section_area(flat(-40, -250, 250), flat(-44, -200, 300), a_prism(width=600))
    assert area.left == -200
    assert area.right == 250


def test_two_surveys_that_do_not_overlap_have_no_section() -> None:
    before = flat(-40, -300, -100)
    after = flat(-44, 100, 300)
    with pytest.raises(MissingError):
        section_area(before, after, a_prism())


def test_two_surveys_on_different_stations_do_not_pair() -> None:
    other = Profile(
        Station.parse("101+00"),
        (Point(-300, Elevation.of_feet(-44)), Point(300, Elevation.of_feet(-44))),
    )
    with pytest.raises(MissingError):
        section_area(flat(-40), other, a_prism())
