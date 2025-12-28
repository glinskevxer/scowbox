"""Applying modifications in signature order."""

from __future__ import annotations

import datetime as dt

import pytest

from scowbox.errors import RuleError
from scowbox.model.contract import Contract, LineItem, Unit
from scowbox.model.modification import Change, Modification
from scowbox.pay.modified import apply, in_order
from scowbox.units.money import Money

AWARD = dt.date(2025, 1, 20)
NTP = dt.date(2025, 2, 3)

BASE = Contract(
    number="W912PM-25-C-0014",
    awarded=AWARD,
    notice_to_proceed=NTP,
    days=365,
    retainage=0.05,
    liquidated=Money.parse("$3,400.00"),
    items=(LineItem("LI-0001", "Dredging, base", Unit.CUBIC_YARD, Money.parse("$7.35"), "base"),),
)


def a_time(number: str, day: dt.date, days: int) -> Modification:
    return Modification(number, day, Change.TIME, "Time extension", days=days)


def a_price(number: str, day: dt.date, price: str, item: str = "LI-0001") -> Modification:
    return Modification(number, day, Change.PRICE, "Rock", item=item, price=Money.parse(price))


def an_item(number: str, day: dt.date, item: str, price: str) -> Modification:
    return Modification(
        number, day, Change.ITEM, "Relocation trawling", item=item, price=Money.parse(price)
    )


def test_no_modifications_leave_the_contract_alone() -> None:
    got = apply(BASE, [])
    assert got.contract == BASE
    assert got.count == 0
    assert got.added_days == 0


def test_a_time_extension_lengthens_the_contract() -> None:
    got = apply(BASE, [a_time("P00003", dt.date(2025, 6, 1), 45)])
    assert got.contract.days == 410
    assert got.added_days == 45
    assert got.contract.completion == NTP + dt.timedelta(days=410)


def test_two_time_extensions_add_up() -> None:
    got = apply(
        BASE,
        [a_time("P00003", dt.date(2025, 6, 1), 45), a_time("P00005", dt.date(2025, 9, 1), 20)],
    )
    assert got.added_days == 65


def test_a_price_change_reprices_the_item() -> None:
    got = apply(BASE, [a_price("P00004", dt.date(2025, 7, 1), "$9.10")])
    assert got.contract.item("LI-0001").unit_price == Money.parse("$9.10")


def test_a_price_change_keeps_the_group_and_the_bid_quantity() -> None:
    got = apply(BASE, [a_price("P00004", dt.date(2025, 7, 1), "$9.10")])
    item = got.contract.item("LI-0001")
    assert item.group == "base"
    assert item.unit is Unit.CUBIC_YARD


def test_the_later_price_wins() -> None:
    got = apply(
        BASE,
        [
            a_price("P00006", dt.date(2025, 9, 1), "$10.10"),
            a_price("P00004", dt.date(2025, 7, 1), "$9.10"),
        ],
    )
    assert got.contract.item("LI-0001").unit_price == Money.parse("$10.10")


def test_two_on_one_day_order_by_number() -> None:
    ordered = in_order(
        [
            a_price("P00006", dt.date(2025, 7, 1), "$10.10"),
            a_price("P00004", dt.date(2025, 7, 1), "$9.10"),
        ]
    )
    assert [m.number for m in ordered] == ["P00004", "P00006"]


def test_a_new_item_joins_the_schedule() -> None:
    got = apply(BASE, [an_item("P00007", dt.date(2025, 8, 1), "LI-0020", "$85,000.00")])
    assert got.contract.item("LI-0020").unit is Unit.LUMP_SUM
    assert len(got.contract.items) == 2


def test_adding_an_item_the_contract_already_has_is_refused() -> None:
    with pytest.raises(RuleError, match="already has"):
        apply(BASE, [an_item("P00007", dt.date(2025, 8, 1), "LI-0001", "$85,000.00")])


def test_repricing_an_item_the_contract_has_not_is_refused() -> None:
    with pytest.raises(RuleError, match="has not"):
        apply(BASE, [a_price("P00004", dt.date(2025, 7, 1), "$9.10", item="LI-0099")])


def test_an_item_added_then_repriced_takes_the_later_price() -> None:
    got = apply(
        BASE,
        [
            an_item("P00007", dt.date(2025, 8, 1), "LI-0020", "$85,000.00"),
            a_price("P00009", dt.date(2025, 10, 1), "$92,000.00", item="LI-0020"),
        ],
    )
    assert got.contract.item("LI-0020").unit_price == Money.parse("$92,000.00")


def test_the_applied_numbers_come_back_in_order() -> None:
    got = apply(
        BASE,
        [a_time("P00005", dt.date(2025, 9, 1), 20), a_time("P00003", dt.date(2025, 6, 1), 45)],
    )
    assert got.numbers == ("P00003", "P00005")
