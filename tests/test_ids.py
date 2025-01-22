"""Identifier shapes, and the ordering that plain text sorting gets wrong."""

from __future__ import annotations

import pytest

from scowbox.errors import FieldError, MissingError
from scowbox.ids import (
    KINDS,
    format_ident,
    is_ident,
    kind,
    kind_of,
    parse_ident,
    sort_key,
)


def test_prefixes_are_unique_across_kinds() -> None:
    prefixes = [k.prefix for k in KINDS]
    assert len(set(prefixes)) == len(prefixes)


def test_names_are_unique_across_kinds() -> None:
    names = [k.name for k in KINDS]
    assert len(set(names)) == len(names)


def test_format_pads_to_the_declared_width() -> None:
    assert format_ident("reach", 12) == "RCH-012"
    assert format_ident("trip", 4188) == "TR-04188"
    assert format_ident("estimate", 7) == "EST-007"


def test_format_refuses_a_number_that_does_not_fit() -> None:
    with pytest.raises(FieldError):
        format_ident("reach", 1000)
    with pytest.raises(FieldError):
        format_ident("reach", 0)


def test_parse_is_the_inverse_of_format() -> None:
    for shape in KINDS:
        assert parse_ident(shape.name, format_ident(shape.name, 42)) == 42


def test_parse_refuses_the_wrong_family() -> None:
    with pytest.raises(FieldError) as caught:
        parse_ident("reach", "SV-0031")
    assert caught.value.field == "reach"


def test_parse_refuses_a_short_number() -> None:
    with pytest.raises(FieldError):
        parse_ident("trip", "TR-418")


def test_is_ident_does_not_raise() -> None:
    assert is_ident("survey", "SV-0031")
    assert not is_ident("survey", "SV-31")
    assert not is_ident("survey", "RCH-012")


def test_unknown_kind_is_a_missing_error() -> None:
    with pytest.raises(MissingError):
        kind("barge")


def test_kind_of_reads_the_prefix() -> None:
    assert kind_of("PA-004").name == "placement"
    assert kind_of("SH-00021").name == "shift"


def test_kind_of_refuses_a_stranger() -> None:
    with pytest.raises(FieldError):
        kind_of("BARGE-1")
    with pytest.raises(FieldError):
        kind_of("TR-1")


def test_sort_key_orders_by_number_not_by_text() -> None:
    trips = ["TR-00100", "TR-00099", "TR-00021"]
    assert sorted(trips, key=sort_key) == ["TR-00021", "TR-00099", "TR-00100"]
    assert sorted(trips) == ["TR-00021", "TR-00099", "TR-00100"]


def test_sort_key_groups_families_together() -> None:
    mixed = ["TR-00100", "RCH-004", "TR-00021", "RCH-012"]
    assert sorted(mixed, key=sort_key) == ["RCH-004", "RCH-012", "TR-00021", "TR-00100"]
