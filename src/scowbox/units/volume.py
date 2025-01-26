"""Cubic yards.

Everything on a dredging contract is paid by the cubic yard, and everything is
measured in feet. The division by 27 happens here, once, so that no rule module
carries a bare literal 27 that a reader has to interpret.

Held in hundredths of a cubic yard. A reach is a sum of a few hundred section
volumes and a pay estimate is a sum of a few dozen reaches, so the accumulation
is deep enough that float error reaches the tenth a quantity is reported to.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Self

from scowbox.errors import FieldError

CUBIC_FEET_PER_YARD = 27


@dataclass(frozen=True, order=True)
class Yards:
    """A volume in hundredths of a cubic yard."""

    hundredths: int

    @classmethod
    def of_yards(cls, yards: float) -> Self:
        return cls(round(yards * 100))

    @classmethod
    def of_cubic_feet(cls, cubic_feet: float) -> Self:
        """Convert from the feet the survey and the box measure work in."""
        return cls(round(cubic_feet * 100 / CUBIC_FEET_PER_YARD))

    @classmethod
    def zero(cls) -> Self:
        return cls(0)

    @property
    def yards(self) -> float:
        return self.hundredths / 100

    @property
    def cubic_feet(self) -> float:
        return self.yards * CUBIC_FEET_PER_YARD

    def __add__(self, other: Yards) -> Yards:
        return Yards(self.hundredths + other.hundredths)

    def __sub__(self, other: Yards) -> Yards:
        return Yards(self.hundredths - other.hundredths)

    def __neg__(self) -> Yards:
        return Yards(-self.hundredths)

    def scaled(self, factor: float) -> Yards:
        """Apply a bulking factor or a deduction ratio."""
        if factor < 0:
            raise FieldError("factor", "a volume factor cannot be negative")
        return Yards(round(self.hundredths * factor))

    def clipped(self) -> Yards:
        """Nothing below zero. A section that filled in removed no material."""
        return self if self.hundredths > 0 else Yards(0)

    def __str__(self) -> str:
        return f"{self.yards:,.2f} cy"

    def rounded(self) -> str:
        """Whole cubic yards, which is how a pay estimate line reads."""
        return f"{round(self.yards):,} cy"


def total(volumes: Iterable[Yards]) -> Yards:
    """Sum a run of volumes without losing a hundredth on the way."""
    return Yards(sum(v.hundredths for v in volumes))
