"""Repeatability and coverage, the two ways a plausible survey fails."""

from __future__ import annotations

import pytest

from scowbox.datum.reduce import Shot
from scowbox.errors import FieldError
from scowbox.measure.quality import coverage, quality, repeats
from scowbox.model.channel import Template
from scowbox.units.depth import Depth, Elevation
from scowbox.units.station import Station


def a_shot(station: str, offset: float, bed: float) -> Shot:
    return Shot(Station.parse(station), offset, Elevation.of_feet(bed))


def a_template(width: float = 600.0) -> Template:
    return Template(bottom_width=width, authorized_depth=Depth.of_feet(42), side_slope=0)


def a_line(station: str, bed: float = -44.0) -> list[Shot]:
    return [a_shot(station, offset, bed) for offset in (-300.0, 0.0, 300.0)]


def test_a_point_sounded_once_is_not_a_repeat() -> None:
    assert repeats(a_line("100+00")) == ()


def test_a_point_sounded_twice_is_a_repeat() -> None:
    found = repeats([a_shot("100+00", 0, -44.0), a_shot("100+00", 0, -44.2)])
    assert len(found) == 1
    assert found[0].readings == 2
    assert found[0].spread == pytest.approx(0.2, abs=0.001)


def test_two_shots_a_foot_apart_are_the_same_point() -> None:
    found = repeats([a_shot("100+00", 0, -44.0), a_shot("100+00", 1.0, -44.2)])
    assert len(found) == 1


def test_two_shots_well_apart_are_two_points() -> None:
    assert repeats([a_shot("100+00", 0, -44.0), a_shot("100+00", 50.0, -44.2)]) == ()


def test_a_narrower_nearby_splits_them_again() -> None:
    shots = [a_shot("100+00", 0, -44.0), a_shot("100+00", 1.0, -44.2)]
    assert repeats(shots, nearby=0.1) == ()


def test_a_nearby_of_nothing_is_refused() -> None:
    with pytest.raises(FieldError):
        repeats([], nearby=0)


def test_the_worst_disagreement_comes_first() -> None:
    found = repeats(
        [
            a_shot("100+00", 0, -44.0),
            a_shot("100+00", 0, -44.2),
            a_shot("101+00", 0, -44.0),
            a_shot("101+00", 0, -45.0),
        ]
    )
    assert found[0].station == Station.parse("101+00")
    assert found[0].spread == pytest.approx(1.0, abs=0.001)


def test_a_disagreement_inside_the_tolerance_is_kept_but_not_flagged() -> None:
    found = repeats([a_shot("100+00", 0, -44.0), a_shot("100+00", 0, -44.4)])
    assert found[0].inside


def test_a_disagreement_past_the_tolerance_is_flagged() -> None:
    found = repeats([a_shot("100+00", 0, -44.0), a_shot("100+00", 0, -44.7)])
    assert not found[0].inside


def test_a_station_that_spans_the_template_is_covered() -> None:
    assert coverage(a_line("100+00"), a_template()) == ()


def test_a_station_that_falls_short_is_named() -> None:
    short = [a_shot("100+00", -100.0, -44.0), a_shot("100+00", 100.0, -44.0)]
    found = coverage(short, a_template())
    assert found[0][0] == Station.parse("100+00")
    assert found[0][1] == 200.0
    assert found[0][2] == 540.0


def test_a_gentler_share_accepts_a_narrower_survey() -> None:
    short = [a_shot("100+00", -200.0, -44.0), a_shot("100+00", 200.0, -44.0)]
    assert coverage(short, a_template(), share=0.6) == ()


def test_a_share_outside_the_range_is_refused() -> None:
    with pytest.raises(FieldError):
        coverage([], a_template(), share=0)
    with pytest.raises(FieldError):
        coverage([], a_template(), share=1.5)


def test_a_sound_survey_is_repeatable_and_covered() -> None:
    got = quality([*a_line("100+00"), *a_line("101+00")], a_template())
    assert got.sound
    assert got.shots == 6
    assert got.stations == 2
    assert got.worst == 0.0


def test_a_survey_that_disagrees_with_itself_is_not_sound() -> None:
    got = quality([*a_line("100+00"), a_shot("100+00", 0, -45.0)], a_template())
    assert not got.repeatable
    assert not got.sound
    assert len(got.outside) == 1


def test_a_survey_that_missed_the_edges_is_not_sound() -> None:
    got = quality([a_shot("100+00", -100.0, -44.0), a_shot("100+00", 100.0, -44.0)], a_template())
    assert got.repeatable
    assert not got.covered
    assert not got.sound
