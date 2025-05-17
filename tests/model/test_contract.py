"""The bid schedule, contract time and the arithmetic hanging off it."""

from __future__ import annotations

import datetime as dt

import pytest

from scowbox.errors import DuplicateError, FieldError, MissingError, RangeError
from scowbox.model.contract import Contract, LineItem, Unit
from scowbox.units.money import Money

AWARD = dt.date(2025, 1, 20)
NTP = dt.date(2025, 2, 3)


def an_item(**over: object) -> LineItem:
    fields: dict[str, object] = {
        "ident": "LI-0001",
        "description": "Maintenance dredging, base reaches",
        "unit": Unit.CUBIC_YARD,
        "unit_price": Money.parse("$7.35"),
        "group": "base",
        "estimated": 480000.0,
    }
    fields.update(over)
    return LineItem(**fields)  # type: ignore[arg-type]


def a_lump(ident: str = "LI-0009") -> LineItem:
    return LineItem(
        ident=ident,
        description="Mobilisation and demobilisation",
        unit=Unit.LUMP_SUM,
        unit_price=Money.parse("$1,250,000.00"),
    )


def a_contract(**over: object) -> Contract:
    fields: dict[str, object] = {
        "number": "W912PM-25-C-0014",
        "awarded": AWARD,
        "notice_to_proceed": NTP,
        "days": 180,
        "retainage": 0.05,
        "liquidated": Money.parse("$3,400.00"),
        "items": (an_item(), a_lump()),
    }
    fields.update(over)
    return Contract(**fields)  # type: ignore[arg-type]


def test_only_a_cubic_yard_item_is_extended_by_quantity() -> None:
    assert Unit.CUBIC_YARD.by_quantity
    assert not Unit.LUMP_SUM.by_quantity
    assert not Unit.DAY.by_quantity


def test_a_cubic_yard_item_needs_a_pay_group() -> None:
    with pytest.raises(FieldError) as caught:
        an_item(group="")
    assert caught.value.field == "group"


def test_a_lump_sum_with_a_pay_group_is_refused() -> None:
    with pytest.raises(FieldError):
        LineItem("LI-0009", "Mob", Unit.LUMP_SUM, Money.parse("$1.00"), group="base")


def test_an_item_needs_an_identifier_a_description_and_a_price() -> None:
    with pytest.raises(FieldError):
        an_item(ident="RCH-012")
    with pytest.raises(FieldError):
        an_item(description=" ")
    with pytest.raises(FieldError):
        an_item(unit_price=Money.zero())


def test_a_negative_bid_quantity_is_refused() -> None:
    with pytest.raises(FieldError):
        an_item(estimated=-1)


def test_completion_is_the_days_after_notice_to_proceed() -> None:
    assert a_contract().completion == NTP + dt.timedelta(days=180)


def test_an_item_can_be_found_by_identifier() -> None:
    assert a_contract().item("LI-0009").unit is Unit.LUMP_SUM


def test_an_item_that_is_not_there_is_missing() -> None:
    with pytest.raises(MissingError):
        a_contract().item("LI-0099")


def test_a_pay_group_finds_its_cubic_yard_item() -> None:
    assert a_contract().for_group("base").ident == "LI-0001"


def test_a_pay_group_with_no_item_is_missing() -> None:
    with pytest.raises(MissingError):
        a_contract().for_group("entrance")


def test_two_items_with_one_identifier_are_refused() -> None:
    with pytest.raises(DuplicateError):
        a_contract(items=(an_item(), an_item()))


def test_two_cubic_yard_items_on_one_group_are_refused() -> None:
    with pytest.raises(DuplicateError):
        a_contract(items=(an_item(), an_item(ident="LI-0002")))


def test_two_lump_sums_are_fine() -> None:
    contract = a_contract(items=(a_lump("LI-0009"), a_lump("LI-0010")))
    assert len(contract.items) == 2


def test_notice_to_proceed_cannot_precede_award() -> None:
    with pytest.raises(FieldError):
        a_contract(notice_to_proceed=dt.date(2025, 1, 1))


def test_retainage_past_the_ceiling_is_refused() -> None:
    with pytest.raises(RangeError):
        a_contract(retainage=0.2)


def test_a_contract_with_no_days_is_refused() -> None:
    with pytest.raises(FieldError):
        a_contract(days=0)


def test_finishing_early_is_not_late() -> None:
    contract = a_contract()
    assert contract.days_late(contract.completion - dt.timedelta(days=3)) == 0


def test_finishing_late_counts_the_days() -> None:
    contract = a_contract()
    assert contract.days_late(contract.completion + dt.timedelta(days=12)) == 12


def test_a_time_extension_moves_the_day_it_is_counted_from() -> None:
    contract = a_contract()
    late = contract.completion + dt.timedelta(days=12)
    assert contract.days_late(late, extension=5) == 7
    assert contract.days_late(late, extension=20) == 0
