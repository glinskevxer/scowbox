"""Placement areas, what each kind of ground takes, and tickets."""

from __future__ import annotations

import datetime as dt

import pytest

from scowbox.errors import FieldError
from scowbox.model.placement import Grade, Ground, PlacementArea, PlacementTicket
from scowbox.units.clock import moment
from scowbox.units.volume import Yards

DAY = dt.date(2025, 4, 2)


def an_area(**over: object) -> PlacementArea:
    fields: dict[str, object] = {
        "ident": "PA-002",
        "name": "Wilmington ODMDS",
        "ground": Ground.OCEAN,
        "permit": "SAW-2019-01142",
        "capacity": None,
    }
    fields.update(over)
    return PlacementArea(**fields)  # type: ignore[arg-type]


def a_ticket(**over: object) -> PlacementTicket:
    fields: dict[str, object] = {
        "trip": "TR-04188",
        "area": "PA-002",
        "released": moment(DAY, "11:20"),
        "yards": Yards.of_yards(1800),
        "grade": Grade.SUITABLE,
    }
    fields.update(over)
    return PlacementTicket(**fields)  # type: ignore[arg-type]


def test_an_ocean_site_takes_suitable_material() -> None:
    assert an_area().takes(Grade.SUITABLE)
    assert not an_area().takes(Grade.UNSUITABLE)


def test_a_beach_takes_only_beach_quality_sand() -> None:
    beach = an_area(ground=Ground.BEACH)
    assert beach.takes(Grade.BEACH_QUALITY)
    assert not beach.takes(Grade.SUITABLE)
    assert not beach.takes(Grade.UNSUITABLE)


def test_an_ocean_site_takes_beach_quality_too() -> None:
    assert an_area().takes(Grade.BEACH_QUALITY)


def test_a_confined_facility_takes_everything() -> None:
    upland = an_area(ground=Ground.UPLAND, capacity=Yards.of_yards(500000))
    assert all(upland.takes(grade) for grade in Grade)


def test_only_a_confined_facility_fills_up() -> None:
    assert Ground.UPLAND.fills
    assert not Ground.OCEAN.fills
    assert not Ground.BEACH.fills


def test_a_confined_facility_needs_a_capacity() -> None:
    with pytest.raises(FieldError) as caught:
        an_area(ground=Ground.UPLAND)
    assert caught.value.field == "capacity"


def test_an_ocean_site_does_not_need_one() -> None:
    assert an_area().capacity is None


def test_a_capacity_of_nothing_is_refused() -> None:
    with pytest.raises(FieldError):
        an_area(ground=Ground.UPLAND, capacity=Yards.zero())


def test_an_area_needs_an_identifier_a_name_and_a_permit() -> None:
    with pytest.raises(FieldError):
        an_area(ident="RCH-012")
    with pytest.raises(FieldError):
        an_area(name=" ")
    with pytest.raises(FieldError):
        an_area(permit="")


def test_a_ticket_checks_both_its_identifiers() -> None:
    with pytest.raises(FieldError):
        a_ticket(trip="PA-002")
    with pytest.raises(FieldError):
        a_ticket(area="TR-04188")


def test_a_ticket_carries_a_load_and_a_zoned_time() -> None:
    with pytest.raises(FieldError):
        a_ticket(yards=Yards.zero())
    with pytest.raises(FieldError):
        a_ticket(released=dt.datetime(2025, 4, 2, 11, 20))  # noqa: DTZ001
