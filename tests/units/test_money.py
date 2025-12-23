"""Money in cents, and the single rounding point an extension goes through."""

from __future__ import annotations

import pytest

from scowbox.errors import FieldError
from scowbox.units.money import Money, extend, half_up, total
from scowbox.units.volume import Yards


def test_dollars_become_whole_cents() -> None:
    assert Money.of_dollars(12.34).cents == 1234
    assert Money.of_dollars(0.005).cents == 1


def test_parse_reads_a_bid_schedule_amount() -> None:
    assert Money.parse("$12.34") == Money(1234)
    assert Money.parse("12.34") == Money(1234)
    assert Money.parse("$1,250,000") == Money(125000000)
    assert Money.parse("$12.3") == Money(1230)


def test_parse_reads_a_credit() -> None:
    assert Money.parse("-$12.34") == Money(-1234)


@pytest.mark.parametrize("text", ["", "twelve", "$12.345", "12.34.56"])
def test_parse_refuses_anything_else(text: str) -> None:
    with pytest.raises(FieldError):
        Money.parse(text)


def test_half_up_does_not_round_to_even() -> None:
    assert half_up(0.5) == 1
    assert half_up(1.5) == 2
    assert half_up(-0.5) == -1
    assert round(0.5) == 0


def test_text_carries_the_sign_outside_the_dollar() -> None:
    assert str(Money(-1234)) == "-$12.34"
    assert str(Money(125000000)) == "$1,250,000.00"


def test_addition_and_subtraction_stay_exact() -> None:
    assert Money.parse("$10.10") + Money.parse("$0.90") == Money.parse("$11.00")
    assert Money.parse("$10.10") - Money.parse("$0.10") == Money.parse("$10.00")


def test_total_matches_repeated_addition() -> None:
    assert total([Money(1), Money(2), Money(3)]) == Money(6)


def test_portion_takes_retainage_and_rounds_half_up() -> None:
    assert Money.parse("$1,000.00").portion(0.05) == Money.parse("$50.00")
    assert Money(101).portion(0.5) == Money(51)


def test_portion_of_a_credit_rounds_away_from_zero() -> None:
    assert Money(-101).portion(0.5) == Money(-51)


def test_an_extension_rounds_once_only() -> None:
    price = Money.parse("$7.35")
    assert extend(price, Yards.of_yards(1000)) == Money.parse("$7,350.00")
    assert extend(price, Yards.of_yards(1000.5)) == Money.parse("$7,353.68")


def test_extending_the_parts_can_differ_from_extending_the_sum() -> None:
    price = Money.parse("$7.35")
    parts = [Yards.of_yards(0.07), Yards.of_yards(0.07), Yards.of_yards(0.07)]
    piecemeal = total([extend(price, p) for p in parts])
    at_once = extend(price, Yards.of_yards(0.21))
    assert piecemeal != at_once
    assert at_once == Money(154)
