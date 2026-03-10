"""When a confined disposal facility runs out.

The question a district asks in February and needs the answer to in January.
It is arithmetic on the tickets already written: what has gone in, over how
many days, and how much room is left.

Two things it refuses to do. It will not forecast from a single day's tickets,
because one day is a rate of nothing over nothing. And it will not forecast an
ocean site, which has no capacity to run out of; asking produces a forecast
that says so rather than a very large number.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from scowbox.errors import FieldError
from scowbox.model.placement import PlacementArea, PlacementTicket
from scowbox.units.volume import Yards, total

MIN_DAYS = 2


@dataclass(frozen=True)
class Forecast:
    """What a placement area holds and how long it has left."""

    area: str
    placed: Yards
    capacity: Yards | None
    loads: int
    days: int
    through: dt.date

    @property
    def remaining(self) -> Yards | None:
        if self.capacity is None:
            return None
        return self.capacity - self.placed

    @property
    def a_day(self) -> float | None:
        """Cubic yards a day over the period the tickets cover."""
        if self.days < MIN_DAYS or self.loads == 0:
            return None
        return round(self.placed.yards / self.days, 1)

    @property
    def average_load(self) -> Yards | None:
        if self.loads == 0:
            return None
        return Yards(self.placed.hundredths // self.loads)

    @property
    def loads_left(self) -> int | None:
        left = self.remaining
        mean = self.average_load
        if left is None or mean is None or mean.hundredths <= 0:
            return None
        return max(left.hundredths // mean.hundredths, 0)

    @property
    def days_left(self) -> int | None:
        left = self.remaining
        rate = self.a_day
        if left is None or rate is None or rate <= 0:
            return None
        return max(int(left.yards // rate), 0)

    @property
    def full_on(self) -> dt.date | None:
        left = self.days_left
        if left is None:
            return None
        return self.through + dt.timedelta(days=left)

    @property
    def open_ground(self) -> bool:
        """True where there is no capacity to run out of."""
        return self.capacity is None


def forecast(area: PlacementArea, tickets: Iterable[PlacementTicket], through: dt.date) -> Forecast:
    """Work out how long an area has left at the rate its tickets show."""
    mine: Sequence[PlacementTicket] = [t for t in tickets if t.area == area.ident]
    days = _span(mine, through)
    return Forecast(
        area=area.ident,
        placed=total(t.yards for t in mine),
        capacity=area.capacity,
        loads=len(mine),
        days=days,
        through=through,
    )


def _span(tickets: Sequence[PlacementTicket], through: dt.date) -> int:
    if not tickets:
        return 0
    first = min(t.released.date() for t in tickets)
    if through < first:
        raise FieldError("through", "a forecast runs to a day on or after the first ticket")
    return (through - first).days + 1
