"""Money, in whole cents.

A pay estimate is arithmetic on a contract, and a contract is arithmetic
somebody checks by hand. Cents are integers, extensions round once at the point
of extension, and the rounding rule is written down here rather than left to
whichever module got there first.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Self

from scowbox.errors import FieldError
from scowbox.units.volume import Yards


def half_up(value: float) -> int:
    """Round half away from zero, which is what a clerk with a pencil does.

    Python rounds half to even, so ``round(0.5)`` is 0 and ``round(1.5)`` is 2.
    That is the right default for a long statistical sum and the wrong one for
    an amount somebody is going to add up again by hand.
    """
    return int(value + (0.5 if value >= 0 else -0.5))


_TEXT = re.compile(r"^(-)?\$?([0-9,]+)(?:\.([0-9]{1,2}))?$")


@dataclass(frozen=True, order=True)
class Money:
    """An amount in whole cents."""

    cents: int

    @classmethod
    def of_dollars(cls, dollars: float) -> Self:
        return cls(half_up(dollars * 100))

    @classmethod
    def parse(cls, text: str) -> Self:
        """Read an amount as it is typed on a bid schedule."""
        match = _TEXT.match(text.strip())
        if match is None:
            raise FieldError("amount", f"{text!r} is not an amount of money")
        sign, whole, frac = match.groups()
        cents = int(whole.replace(",", "")) * 100 + int((frac or "0").ljust(2, "0"))
        return cls(-cents if sign else cents)

    @classmethod
    def zero(cls) -> Self:
        return cls(0)

    @property
    def dollars(self) -> float:
        return self.cents / 100

    def __add__(self, other: Money) -> Money:
        return Money(self.cents + other.cents)

    def __sub__(self, other: Money) -> Money:
        return Money(self.cents - other.cents)

    def __neg__(self) -> Money:
        return Money(-self.cents)

    def portion(self, fraction: float) -> Money:
        """A percentage of an amount, such as retainage. Rounds half away from zero."""
        return Money(half_up(self.cents * fraction))

    def __str__(self) -> str:
        sign = "-" if self.cents < 0 else ""
        return f"{sign}${abs(self.cents) / 100:,.2f}"


def extend(unit_price: Money, quantity: Yards) -> Money:
    """Price a quantity of cubic yards at a unit price.

    Rounded once, here. A line item that extended each section and summed the
    extensions would answer a different number than the schedule of values
    does, and the schedule of values is the one the owner pays against.
    """
    return Money(half_up(unit_price.cents * quantity.hundredths / 100))


def total(amounts: Iterable[Money]) -> Money:
    """Add a run of amounts without losing a cent on the way."""
    return Money(sum(a.cents for a in amounts))
