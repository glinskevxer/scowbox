"""Corridors, the tie rule, and the shots that land in none of them."""

from __future__ import annotations

import pytest

from scowbox.datum.reduce import Shot
from scowbox.errors import FieldError
from scowbox.section.gather import gather, nearest_station
from scowbox.units.depth import Elevation
from scowbox.units.station import Station

SECTIONS = [Station.parse("100+00"), Station.parse("101+00"), Station.parse("102+00")]


def a_shot(station: str, offset: float = 0.0, bed: float = -44.0) -> Shot:
    return Shot(Station.parse(station), offset, Elevation.of_feet(bed))


def test_a_shot_on_a_section_belongs_to_it() -> None:
    assert nearest_station(a_shot("101+00"), SECTIONS, 10) == Station.parse("101+00")


def test_a_shot_inside_the_corridor_is_pulled_on() -> None:
    assert nearest_station(a_shot("101+04"), SECTIONS, 10) == Station.parse("101+00")
    assert nearest_station(a_shot("100+96"), SECTIONS, 10) == Station.parse("101+00")


def test_a_shot_outside_every_corridor_belongs_to_nothing() -> None:
    assert nearest_station(a_shot("100+50"), SECTIONS, 10) is None


def test_a_tie_goes_to_the_section_behind() -> None:
    behind = nearest_station(a_shot("100+50"), SECTIONS, 100)
    assert behind == Station.parse("100+00")


def test_a_wider_corridor_catches_more() -> None:
    assert nearest_station(a_shot("100+40"), SECTIONS, 10) is None
    assert nearest_station(a_shot("100+40"), SECTIONS, 100) == Station.parse("100+00")


def test_gathered_shots_take_the_station_of_their_section() -> None:
    caught = gather([a_shot("100+04", -50), a_shot("100+00", 50)], SECTIONS)
    assert len(caught.profiles) == 1
    assert caught.profiles[0].station == Station.parse("100+00")
    assert caught.profiles[0].offsets() == (-50.0, 50.0)


def test_strays_are_counted_not_dropped_quietly() -> None:
    caught = gather(
        [a_shot("100+00", -50), a_shot("100+00", 50), a_shot("100+50"), a_shot("101+50")],
        SECTIONS,
    )
    assert caught.stray == 2
    assert caught.caught == 2
    assert caught.share_used == 0.5


def test_a_section_with_one_shot_is_reported_as_thin() -> None:
    caught = gather([a_shot("100+00"), a_shot("101+00", -50), a_shot("101+00", 50)], SECTIONS)
    assert caught.thin == (Station.parse("100+00"), Station.parse("102+00"))
    assert len(caught.profiles) == 1


def test_two_shots_on_one_offset_do_not_make_a_line() -> None:
    caught = gather([a_shot("100+00", 0, -44), a_shot("100+02", 0, -46)], SECTIONS)
    assert caught.thin[0] == Station.parse("100+00")
    assert caught.profiles == ()


def test_nothing_offered_is_no_share_at_all() -> None:
    caught = gather([], SECTIONS)
    assert caught.share_used == 0.0
    assert caught.caught == 0


def test_sections_come_back_in_station_order() -> None:
    shuffled = list(reversed(SECTIONS))
    shots = [a_shot(str(s), o) for s in shuffled for o in (-50, 50)]
    caught = gather(shots, shuffled)
    assert [str(p.station) for p in caught.profiles] == ["100+00", "101+00", "102+00"]


def test_a_corridor_needs_a_width() -> None:
    with pytest.raises(FieldError):
        gather([], SECTIONS, corridor=0)


def test_gathering_onto_no_sections_is_refused() -> None:
    with pytest.raises(FieldError):
        gather([a_shot("100+00")], [])
