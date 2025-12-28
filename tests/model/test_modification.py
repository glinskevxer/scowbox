"""What a modification record has to carry for each kind of change."""

from __future__ import annotations

import datetime as dt

import pytest

from scowbox.errors import FieldError
from scowbox.model.modification import Change, Modification
from scowbox.units.money import Money

DAY = dt.date(2026, 1, 12)


def a_time_change(**over: object) -> Modification:
    fields: dict[str, object] = {
        "number": "P00003",
        "signed_on": DAY,
        "change": Change.TIME,
        "description": "Time extension for the sturgeon window",
        "days": 45,
    }
    fields.update(over)
    return Modification(**fields)  # type: ignore[arg-type]


def a_price_change(**over: object) -> Modification:
    fields: dict[str, object] = {
        "number": "P00004",
        "signed_on": DAY,
        "change": Change.PRICE,
        "description": "Rock in the entrance",
        "item": "LI-0001",
        "price": Money.parse("$9.10"),
    }
    fields.update(over)
    return Modification(**fields)  # type: ignore[arg-type]


def test_each_kind_needs_a_different_field() -> None:
    assert Change.TIME.needs_days
    assert not Change.TIME.needs_item
    assert Change.PRICE.needs_item
    assert Change.ITEM.needs_price


def test_a_time_extension_carries_days() -> None:
    assert a_time_change().days == 45


def test_a_time_extension_of_nothing_is_refused() -> None:
    with pytest.raises(FieldError) as caught:
        a_time_change(days=0)
    assert caught.value.field == "days"


def test_a_time_extension_can_take_days_away() -> None:
    assert a_time_change(days=-10).days == -10


def test_a_time_extension_names_no_item_and_no_price() -> None:
    with pytest.raises(FieldError):
        a_time_change(item="LI-0001")
    with pytest.raises(FieldError):
        a_time_change(price=Money.parse("$1.00"))


def test_a_price_change_names_an_item_and_a_price() -> None:
    assert a_price_change().item == "LI-0001"
    with pytest.raises(FieldError):
        a_price_change(item="")
    with pytest.raises(FieldError):
        a_price_change(price=None)


def test_a_price_change_changes_no_days() -> None:
    with pytest.raises(FieldError):
        a_price_change(days=10)


def test_a_price_of_nothing_is_refused() -> None:
    with pytest.raises(FieldError):
        a_price_change(price=Money.zero())


def test_a_modification_is_numbered_and_described() -> None:
    with pytest.raises(FieldError):
        a_time_change(number=" ")
    with pytest.raises(FieldError):
        a_time_change(description="")


def test_a_time_change_describes_itself() -> None:
    assert a_time_change().describe() == ("P00003 (2026-01-12) contract time: +45 days")


def test_a_price_change_describes_itself() -> None:
    assert a_price_change().describe() == ("P00004 (2026-01-12) unit price: LI-0001 at $9.10")
