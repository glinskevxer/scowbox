"""Production: yards against the hours it took to move them.

Against effective hours, not against the clock. A dredge that sat out half a
shift on a closure did not become half as productive; the closure is a
different conversation, and mixing the two makes both of them useless. Downtime
is accounted for on its own in the time report.

Cycle time is the other half. A mechanical dredge's production is bucket cycles
and scow turnaround, and a day where the scows were short is a day where the
yards per hour say something about the tugs rather than about the dredge.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from scowbox.errors import FieldError
from scowbox.model.scow import ScowTrip
from scowbox.model.shift import Shift
from scowbox.units.volume import Yards


@dataclass(frozen=True)
class Rate:
    """What was moved, and what it took."""

    hours: float
    yards: Yards
    trips: int

    def __post_init__(self) -> None:
        if self.hours < 0:
            raise FieldError("hours", "hours worked are not negative")
        if self.trips < 0:
            raise FieldError("trips", "a count of trips is not negative")

    @property
    def yards_per_hour(self) -> float | None:
        """Cubic yards an effective hour, or nothing where no hour was worked."""
        if self.hours <= 0:
            return None
        return round(self.yards.yards / self.hours, 1)

    @property
    def yards_per_trip(self) -> float | None:
        if self.trips <= 0:
            return None
        return round(self.yards.yards / self.trips, 1)

    @property
    def minutes_per_trip(self) -> float | None:
        """Cycle time: how long an effective hour bought between scows."""
        if self.trips <= 0 or self.hours <= 0:
            return None
        return round(self.hours * 60 / self.trips, 1)

    @property
    def worked(self) -> bool:
        return self.hours > 0


def over(shifts: Iterable[Shift], yards: Yards, trips: int) -> Rate:
    """A rate over a run of shifts, with the quantity worked out elsewhere."""
    hours = round(sum(shift.effective_hours for shift in shifts), 2)
    return Rate(hours=hours, yards=yards, trips=trips)


def _trips_by_day(trips: Iterable[ScowTrip]) -> dict[dt.date, int]:
    counted: dict[dt.date, int] = {}
    for trip in trips:
        counted[trip.loaded_on] = counted.get(trip.loaded_on, 0) + 1
    return counted


def by_day(
    shifts: Sequence[Shift], trips: Iterable[ScowTrip], yards_per_trip: Yards
) -> tuple[tuple[dt.date, Rate], ...]:
    """A rate for each day worked, oldest first.

    The quantity for a day is its trips at an average load. A day's survey
    quantity does not exist: the bed is sounded once before and once after, and
    nothing in between says which yard came out on which day.
    """
    hauled = _trips_by_day(trips)
    hours: dict[dt.date, float] = {}
    for shift in shifts:
        hours[shift.day] = round(hours.get(shift.day, 0.0) + shift.effective_hours, 2)
    days = sorted(set(hours) | set(hauled))
    return tuple(
        (
            day,
            Rate(
                hours=hours.get(day, 0.0),
                yards=yards_per_trip.scaled(hauled.get(day, 0)),
                trips=hauled.get(day, 0),
            ),
        )
        for day in days
    )


def best(rates: Iterable[tuple[dt.date, Rate]]) -> tuple[dt.date, Rate] | None:
    """The most productive day worked, or nothing where none was."""
    worked = [pair for pair in rates if pair[1].yards_per_hour is not None]
    if not worked:
        return None
    return max(worked, key=lambda pair: pair[1].yards_per_hour or 0.0)


def worst(rates: Iterable[tuple[dt.date, Rate]]) -> tuple[dt.date, Rate] | None:
    """The least productive day worked, or nothing where none was."""
    worked = [pair for pair in rates if pair[1].yards_per_hour is not None]
    if not worked:
        return None
    return min(worked, key=lambda pair: pair[1].yards_per_hour or 0.0)
