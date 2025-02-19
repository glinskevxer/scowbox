"""Average end area.

Between two sections the volume is the mean of the two end areas times the
distance between them. That is the method the contract specifies and it is the
method the owner's inspector will check with, so it is the only one here.

Two rules travel with it. Sections have to be in station order and distinct,
because a repeated station contributes a slice of no length and a reversed pair
contributes a negative one. And sections cannot be further apart than the
contract's interval allows: average end area assumes the bed changes linearly
between the ends, and over four hundred feet of shoaling it does not.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise

from scowbox.errors import FieldError, RuleError
from scowbox.ids import is_ident
from scowbox.section.area import SectionArea
from scowbox.units.station import Station
from scowbox.units.volume import Yards, total

MAX_SPACING_FEET = 200.0
"""Widest section spacing average end area is trusted over."""


@dataclass(frozen=True)
class Slice:
    """The volume between one pair of sections."""

    begin: Station
    end: Station
    removed: Yards
    pay: Yards

    @property
    def length(self) -> float:
        return self.end - self.begin

    @property
    def overcut(self) -> Yards:
        return self.removed - self.pay


@dataclass(frozen=True)
class ReachVolume:
    """Every slice in one reach, and the totals over them."""

    reach: str
    slices: tuple[Slice, ...]

    def __post_init__(self) -> None:
        if not is_ident("reach", self.reach):
            raise FieldError("reach", f"{self.reach!r} is not a reach identifier")

    @property
    def removed(self) -> Yards:
        return total(s.removed for s in self.slices)

    @property
    def pay(self) -> Yards:
        return total(s.pay for s in self.slices)

    @property
    def overcut(self) -> Yards:
        return self.removed - self.pay

    @property
    def length(self) -> float:
        return round(sum(s.length for s in self.slices), 2)


def between(first: SectionArea, second: SectionArea) -> Slice:
    """Average end area between two sections."""
    length = second.station - first.station
    if length <= 0:
        raise FieldError("sections", f"{second.station} does not lie ahead of {first.station}")
    if length > MAX_SPACING_FEET:
        raise RuleError(
            f"sections {first.station} and {second.station} are {length:g} ft apart,"
            f" past the {MAX_SPACING_FEET:g} ft average end area is trusted over"
        )
    return Slice(
        begin=first.station,
        end=second.station,
        removed=Yards.of_cubic_feet((first.removed + second.removed) / 2 * length),
        pay=Yards.of_cubic_feet((first.pay + second.pay) / 2 * length),
    )


def reach_volume(reach: str, areas: Sequence[SectionArea]) -> ReachVolume:
    """Walk a reach's sections and sum the slices between them."""
    if len(areas) < 2:
        raise FieldError("sections", "a reach volume needs at least two sections")
    ordered = sorted(areas, key=lambda a: a.station.hundredths)
    return ReachVolume(reach, tuple(between(a, b) for a, b in pairwise(ordered)))
