"""Depths and elevations, which are not the same number with a sign on it.

A depth is measured down from a tidal datum and a project engineer says it
positive: the channel is dredged to 42 feet. An elevation is measured up from
that datum and a survey file records it negative: the bed sits at -38.6. Both
appear in the same paperwork, on the same page, and the sign is the only thing
that separates them.

So they are separate types. Adding a depth to an elevation does not compile,
and the conversion between them has a name you can search for.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from scowbox.errors import FieldError, RangeError

DEEPEST_FEET = 200.0
"""No maintenance channel on this coast is deeper than this. A reading past it
is a decimal point in the wrong place, not a trench."""


@dataclass(frozen=True, order=True)
class Depth:
    """Feet below the project datum, positive downward."""

    hundredths: int

    @classmethod
    def of_feet(cls, feet: float) -> Self:
        """Build a depth from feet below datum, rounded to the hundredth."""
        if abs(feet) > DEEPEST_FEET:
            raise RangeError("depth", feet, -DEEPEST_FEET, DEEPEST_FEET)
        return cls(round(feet * 100))

    @property
    def feet(self) -> float:
        return self.hundredths / 100

    def elevation(self) -> Elevation:
        """The same point written the way a survey file writes it."""
        return Elevation(-self.hundredths)

    def deeper_than(self, other: Depth) -> bool:
        return self.hundredths > other.hundredths

    def below(self, feet: float) -> Depth:
        """A depth this many feet further down. Overdepth allowances use this."""
        return Depth(self.hundredths + round(feet * 100))

    def __sub__(self, other: Depth) -> float:
        """Feet between two depths, positive when this one is the deeper."""
        return (self.hundredths - other.hundredths) / 100

    def __str__(self) -> str:
        return f"{self.feet:.2f} ft"


@dataclass(frozen=True, order=True)
class Elevation:
    """Feet relative to the project datum, positive upward."""

    hundredths: int

    @classmethod
    def of_feet(cls, feet: float) -> Self:
        if abs(feet) > DEEPEST_FEET:
            raise RangeError("elevation", feet, -DEEPEST_FEET, DEEPEST_FEET)
        return cls(round(feet * 100))

    @property
    def feet(self) -> float:
        return self.hundredths / 100

    def depth(self) -> Depth:
        """The same point written the way a contract drawing writes it."""
        return Depth(-self.hundredths)

    def above(self, other: Elevation) -> bool:
        return self.hundredths > other.hundredths

    def raised(self, feet: float) -> Elevation:
        return Elevation(self.hundredths + round(feet * 100))

    def __sub__(self, other: Elevation) -> float:
        """Feet between two elevations, positive when this one is the higher."""
        return (self.hundredths - other.hundredths) / 100

    def __str__(self) -> str:
        return f"{self.feet:+.2f} ft"


def parse_depth(text: str) -> Depth:
    """Read a depth written as plain feet, with or without a trailing unit."""
    cleaned = text.strip().removesuffix("ft").strip()
    try:
        feet = float(cleaned)
    except ValueError:
        raise FieldError("depth", f"{text!r} is not a depth in feet") from None
    if feet < 0:
        raise FieldError("depth", "a depth below datum is written positive")
    return Depth.of_feet(feet)
