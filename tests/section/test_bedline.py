"""The bed line across a station, and what it does at its ends."""

from __future__ import annotations

import pytest

from scowbox.datum.reduce import Shot
from scowbox.errors import FieldError, MissingError
from scowbox.section.bedline import Point, Profile
from scowbox.units.depth import Elevation
from scowbox.units.station import Station

STATION = Station.parse("100+00")


def a_profile(*pairs: tuple[float, float]) -> Profile:
    return Profile(STATION, tuple(Point(o, Elevation.of_feet(e)) for o, e in pairs))


def a_shot(offset: float, bed: float, station: str = "100+00") -> Shot:
    return Shot(Station.parse(station), offset, Elevation.of_feet(bed))


def test_a_profile_knows_its_edges_and_width() -> None:
    profile = a_profile((-200, -40), (0, -44), (200, -40))
    assert profile.left == -200
    assert profile.right == 200
    assert profile.width == 400


def test_a_profile_needs_two_points() -> None:
    with pytest.raises(FieldError):
        a_profile((0, -44))


def test_a_profile_runs_left_to_right() -> None:
    with pytest.raises(FieldError):
        a_profile((200, -40), (-200, -40))


def test_a_repeated_offset_in_a_built_profile_is_refused() -> None:
    with pytest.raises(FieldError):
        a_profile((0, -44), (0, -43))


def test_interpolation_is_a_straight_line() -> None:
    profile = a_profile((0, -40), (100, -44))
    assert profile.at(50) == Elevation.of_feet(-42)
    assert profile.at(25) == Elevation.of_feet(-41)


def test_a_shot_offset_comes_back_unchanged() -> None:
    profile = a_profile((0, -40), (100, -44))
    assert profile.at(100) == Elevation.of_feet(-44)


def test_outside_the_shots_there_is_nothing() -> None:
    profile = a_profile((0, -40), (100, -44))
    with pytest.raises(MissingError):
        profile.at(120)
    with pytest.raises(MissingError):
        profile.at(-1)


def test_shots_build_a_profile_in_offset_order() -> None:
    profile = Profile.of_shots(STATION, [a_shot(100, -44), a_shot(-100, -40), a_shot(0, -42)])
    assert profile.offsets() == (-100.0, 0.0, 100.0)


def test_shots_on_another_station_are_left_out() -> None:
    profile = Profile.of_shots(
        STATION, [a_shot(-100, -40), a_shot(100, -44), a_shot(0, -50, station="101+00")]
    )
    assert profile.offsets() == (-100.0, 100.0)


def test_two_shots_on_one_offset_average() -> None:
    profile = Profile.of_shots(STATION, [a_shot(0, -40), a_shot(0, -42), a_shot(100, -44)])
    assert profile.at(0) == Elevation.of_feet(-41)


def test_averaging_does_not_depend_on_the_order_they_arrived() -> None:
    forward = Profile.of_shots(STATION, [a_shot(0, -40), a_shot(0, -42), a_shot(100, -44)])
    backward = Profile.of_shots(STATION, [a_shot(0, -42), a_shot(0, -40), a_shot(100, -44)])
    assert forward == backward


def test_clipping_keeps_the_inside_points_and_interpolates_the_ends() -> None:
    profile = a_profile((-200, -40), (-100, -42), (0, -44), (100, -42), (200, -40))
    clipped = profile.clipped(-150, 150)
    assert clipped.offsets() == (-150.0, -100.0, 0.0, 100.0, 150.0)
    assert clipped.at(-150) == Elevation.of_feet(-41)


def test_clipping_wider_than_the_survey_gives_back_the_survey() -> None:
    profile = a_profile((-100, -42), (0, -44), (100, -42))
    clipped = profile.clipped(-500, 500)
    assert clipped.offsets() == (-100.0, 0.0, 100.0)


def test_clipping_outside_the_survey_finds_nothing() -> None:
    profile = a_profile((-100, -42), (100, -42))
    with pytest.raises(MissingError):
        profile.clipped(200, 300)


def test_a_backwards_clip_is_refused() -> None:
    profile = a_profile((-100, -42), (100, -42))
    with pytest.raises(FieldError):
        profile.clipped(100, -100)
