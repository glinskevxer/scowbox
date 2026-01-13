"""Progress estimates, which are cumulative all the way down."""

from __future__ import annotations

import datetime as dt

import pytest

from scowbox.errors import FieldError, MissingError
from scowbox.model.contract import Contract, LineItem, Unit
from scowbox.pay.estimate import Estimate, EstimateLine, build
from scowbox.units.money import Money
from scowbox.units.volume import Yards

AWARD = dt.date(2025, 1, 20)
NTP = dt.date(2025, 2, 3)
THROUGH = dt.date(2025, 3, 31)

DREDGING = LineItem(
    "LI-0001", "Maintenance dredging, base", Unit.CUBIC_YARD, Money.parse("$7.35"), "base"
)
ENTRANCE = LineItem(
    "LI-0002", "Maintenance dredging, entrance", Unit.CUBIC_YARD, Money.parse("$9.10"), "entrance"
)
MOB = LineItem("LI-0009", "Mobilisation", Unit.LUMP_SUM, Money.parse("$1,250,000.00"))


def a_contract(**over: object) -> Contract:
    fields: dict[str, object] = {
        "number": "W912PM-25-C-0014",
        "awarded": AWARD,
        "notice_to_proceed": NTP,
        "days": 180,
        "retainage": 0.05,
        "liquidated": Money.parse("$3,400.00"),
        "items": (DREDGING, ENTRANCE, MOB),
    }
    fields.update(over)
    return Contract(**fields)  # type: ignore[arg-type]


def test_a_line_earns_its_price_by_its_quantity() -> None:
    line = EstimateLine("LI-0001", "d", Unit.CUBIC_YARD, Money.parse("$7.35"), 1000)
    assert line.earned == Money.parse("$7,350.00")


def test_a_line_knows_what_it_did_this_period() -> None:
    line = EstimateLine("LI-0001", "d", Unit.CUBIC_YARD, Money.parse("$7.35"), 1000, 400)
    assert line.this_period == 600
    assert line.earned_this_period == Money.parse("$4,410.00")


def test_a_negative_quantity_is_refused() -> None:
    with pytest.raises(FieldError):
        EstimateLine("LI-0001", "d", Unit.CUBIC_YARD, Money.parse("$7.35"), -1)


def test_a_lump_sum_past_complete_is_refused() -> None:
    with pytest.raises(FieldError):
        EstimateLine("LI-0009", "m", Unit.LUMP_SUM, Money.parse("$100.00"), 1.5)


def test_an_estimate_carries_every_item_whether_earned_or_not() -> None:
    got = build(a_contract(), 1, THROUGH, {"base": Yards.of_yards(100000)})
    assert [line.item for line in got.lines] == ["LI-0001", "LI-0002", "LI-0009"]
    assert got.line("LI-0002").to_date == 0.0


def test_the_estimate_is_numbered_and_identified() -> None:
    got = build(a_contract(), 3, THROUGH, {})
    assert got.ident == "EST-003"
    assert got.number == 3
    assert got.contract == "W912PM-25-C-0014"


def test_earned_is_the_sum_of_the_lines() -> None:
    got = build(a_contract(), 1, THROUGH, {"base": Yards.of_yards(100000)}, {"LI-0009": 1.0})
    assert got.earned == Money.parse("$735,000.00") + Money.parse("$1,250,000.00")


def test_retainage_comes_off_the_earned_amount() -> None:
    got = build(a_contract(), 1, THROUGH, {"base": Yards.of_yards(100000)})
    assert got.retained == Money.parse("$36,750.00")
    assert got.payable == Money.parse("$698,250.00")


def test_the_first_estimate_owes_everything_payable() -> None:
    got = build(a_contract(), 1, THROUGH, {"base": Yards.of_yards(100000)})
    assert got.due == got.payable


def test_the_second_estimate_owes_only_the_difference() -> None:
    first = build(a_contract(), 1, THROUGH, {"base": Yards.of_yards(100000)})
    second = build(
        a_contract(),
        2,
        dt.date(2025, 4, 30),
        {"base": Yards.of_yards(160000)},
        previous=first,
    )
    assert second.line("LI-0001").previous == 100000
    assert second.line("LI-0001").this_period == 60000
    assert second.due == second.payable - first.payable


def test_retainage_is_taken_on_the_job_not_on_the_month() -> None:
    first = build(a_contract(), 1, THROUGH, {"base": Yards.of_yards(100000)})
    second = build(
        a_contract(), 2, dt.date(2025, 4, 30), {"base": Yards.of_yards(200000)}, previous=first
    )
    assert second.retained == Money.parse("$73,500.00")


def test_liquidated_damages_come_off_the_amount_payable() -> None:
    got = build(a_contract(), 5, THROUGH, {"base": Yards.of_yards(100000)}, days_late=4)
    assert got.liquidated == Money.parse("$13,600.00")
    assert got.payable == Money.parse("$698,250.00") - Money.parse("$13,600.00")


def test_no_damages_where_nothing_is_late() -> None:
    got = build(a_contract(), 1, THROUGH, {"base": Yards.of_yards(100000)})
    assert got.liquidated == Money.zero()


def test_days_late_counted_backwards_is_refused() -> None:
    with pytest.raises(FieldError):
        Estimate("EST-001", "c", 1, THROUGH, 0.05, days_late=-1)


def test_an_estimate_numbered_from_zero_is_refused() -> None:
    with pytest.raises(FieldError):
        Estimate("EST-001", "c", 0, THROUGH, 0.05)


def test_an_estimate_needs_an_estimate_identifier() -> None:
    with pytest.raises(FieldError):
        Estimate("LI-0001", "c", 1, THROUGH, 0.05)


def test_a_line_that_is_not_there_is_missing() -> None:
    got = build(a_contract(), 1, THROUGH, {})
    with pytest.raises(MissingError):
        got.line("LI-0099")


def test_an_item_added_after_the_previous_estimate_starts_at_nothing() -> None:
    first = build(
        Contract("W912PM-25-C-0014", AWARD, NTP, 180, 0.05, Money.parse("$3,400.00"), (DREDGING,)),
        1,
        THROUGH,
        {"base": Yards.of_yards(100000)},
    )
    second = build(
        a_contract(), 2, dt.date(2025, 4, 30), {"entrance": Yards.of_yards(5000)}, previous=first
    )
    assert second.line("LI-0002").previous == 0.0
    assert second.line("LI-0002").this_period == 5000


def test_an_ordinary_estimate_withholds_retainage() -> None:
    got = build(a_contract(), 1, THROUGH, {"base": Yards.of_yards(100000)})
    assert not got.final
    assert got.retained == Money.parse("$36,750.00")
    assert got.released == Money.zero()


def test_the_final_estimate_releases_it() -> None:
    got = build(a_contract(), 9, THROUGH, {"base": Yards.of_yards(100000)}, final=True)
    assert got.final
    assert got.retained == Money.zero()
    assert got.released == Money.parse("$36,750.00")


def test_the_final_estimate_pays_the_retainage_out() -> None:
    running = build(a_contract(), 1, THROUGH, {"base": Yards.of_yards(100000)})
    closing = build(
        a_contract(),
        2,
        dt.date(2025, 4, 30),
        {"base": Yards.of_yards(100000)},
        previous=running,
        final=True,
    )
    assert closing.payable == closing.earned
    assert closing.due == running.retained
