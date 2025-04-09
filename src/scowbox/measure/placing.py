"""Whether a load may be placed where the ticket says it was.

Two questions, asked in this order. Will the ground take material of that
grade, and is there room left in it. The order matters: a beach template with
five hundred thousand yards of room is still not a place to put unsuitable
material, and answering on capacity first produces a report that says a
violation was a near miss.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from scowbox.errors import RuleError
from scowbox.model.placement import Grade, PlacementArea, PlacementTicket
from scowbox.units.volume import Yards, total


@dataclass(frozen=True)
class Standing:
    """What one placement area holds and what it has left."""

    area: str
    placed: Yards
    capacity: Yards | None
    tickets: int

    @property
    def remaining(self) -> Yards | None:
        if self.capacity is None:
            return None
        return self.capacity - self.placed

    @property
    def full(self) -> bool:
        left = self.remaining
        return left is not None and left.hundredths <= 0

    @property
    def share_used(self) -> float | None:
        if self.capacity is None or self.capacity.hundredths == 0:
            return None
        return round(self.placed.hundredths / self.capacity.hundredths, 3)


def standing(area: PlacementArea, tickets: Iterable[PlacementTicket]) -> Standing:
    """Add up what has been placed in one area."""
    mine = [t for t in tickets if t.area == area.ident]
    return Standing(
        area=area.ident,
        placed=total(t.yards for t in mine),
        capacity=area.capacity,
        tickets=len(mine),
    )


def check(area: PlacementArea, held: Standing, grade: Grade, load: Yards) -> None:
    """Raise when a load may not go where it is about to go."""
    if not area.takes(grade):
        raise RuleError(
            f"{area.ident} is a {area.ground.value} and does not take {grade.value} material"
        )
    left = held.remaining
    if left is not None and load.hundredths > left.hundredths:
        raise RuleError(
            f"{area.ident} has {left} left under permit {area.permit}, and the load is {load}"
        )


def would_fill(held: Standing, load: Yards) -> bool:
    """True when this load takes the area to or past its capacity."""
    left = held.remaining
    return left is not None and load.hundredths >= left.hundredths
