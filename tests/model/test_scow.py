"""Scows, box readings and trips, and the four corner rule."""

from __future__ import annotations

import datetime as dt

import pytest

from scowbox.errors import FieldError, RangeError
from scowbox.model.scow import BoxReading, Corner, Scow, ScowTrip

DAY = dt.date(2025, 4, 2)


def a_scow(**over: object) -> Scow:
    fields: dict[str, object] = {
        "ident": "SC-004",
        "name": "Dixie 41",
        "inside_length": 180.0,
        "inside_width": 42.0,
        "inside_depth": 14.0,
    }
    fields.update(over)
    return Scow(**fields)  # type: ignore[arg-type]


def four_readings(light: float = 12.0, loaded: float = 4.0) -> tuple[BoxReading, ...]:
    return tuple(BoxReading(corner, light, loaded) for corner in Corner)


def a_trip(**over: object) -> ScowTrip:
    fields: dict[str, object] = {
        "ident": "TR-04188",
        "scow": "SC-004",
        "reach": "RCH-012",
        "loaded_on": DAY,
        "placement": "PA-002",
        "readings": (),
    }
    fields.update(over)
    return ScowTrip(**fields)  # type: ignore[arg-type]


def test_a_scow_knows_its_plan_area() -> None:
    assert a_scow().box_area == 180 * 42


def test_a_scow_needs_a_scow_identifier_and_a_name() -> None:
    with pytest.raises(FieldError):
        a_scow(ident="TR-04188")
    with pytest.raises(FieldError):
        a_scow(name="   ")


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("inside_length", 0.0),
        ("inside_length", 500.0),
        ("inside_width", -1.0),
        ("inside_depth", 50.0),
    ],
)
def test_a_box_dimension_outside_its_range_is_refused(field_name: str, value: float) -> None:
    with pytest.raises(RangeError) as caught:
        a_scow(**{field_name: value})
    assert caught.value.field == field_name


def test_describe_reads_as_a_measurement_note() -> None:
    assert a_scow().describe() == "SC-004 Dixie 41, 180 by 42 by 14 ft inside"


def test_material_depth_is_light_less_loaded() -> None:
    assert BoxReading(Corner.PORT_BOW, 12.0, 4.0).material == 8.0


def test_an_empty_corner_has_no_material() -> None:
    assert BoxReading(Corner.PORT_BOW, 12.0, 12.0).material == 0.0


def test_a_loaded_reading_deeper_than_light_is_refused() -> None:
    with pytest.raises(FieldError) as caught:
        BoxReading(Corner.PORT_BOW, 4.0, 12.0)
    assert "further down than light" in str(caught.value)


def test_a_reading_measured_upward_is_refused() -> None:
    with pytest.raises(FieldError):
        BoxReading(Corner.PORT_BOW, -1.0, -2.0)


def test_a_trip_starts_unmeasured() -> None:
    assert not a_trip().measured


def test_a_trip_with_four_corners_is_measured() -> None:
    assert a_trip(readings=four_readings()).measured


def test_three_corners_are_not_a_box_measure() -> None:
    with pytest.raises(FieldError):
        a_trip(readings=four_readings()[:3])


def test_the_same_corner_twice_is_refused() -> None:
    doubled = (
        BoxReading(Corner.PORT_BOW, 12.0, 4.0),
        BoxReading(Corner.PORT_BOW, 12.0, 4.0),
        BoxReading(Corner.PORT_STERN, 12.0, 4.0),
        BoxReading(Corner.STARBOARD_BOW, 12.0, 4.0),
    )
    with pytest.raises(FieldError):
        a_trip(readings=doubled)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("ident", "SC-004"),
        ("scow", "TR-04188"),
        ("reach", "SC-004"),
        ("placement", "RCH-012"),
    ],
)
def test_a_trip_checks_every_identifier_it_carries(field_name: str, value: str) -> None:
    with pytest.raises(FieldError) as caught:
        a_trip(**{field_name: value})
    assert caught.value.field == field_name


def test_with_readings_leaves_the_original_alone() -> None:
    plain = a_trip()
    measured = plain.with_readings(four_readings())
    assert not plain.measured
    assert measured.measured
    assert measured.ident == plain.ident
