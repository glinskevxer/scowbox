"""Time lost, and what the contract does about it.

Downtime is sorted three ways at once and the three do not line up. Allowable
time comes back as an extension of contract time. Standby time is paid at the
day rate. Everything else is the contractor's, and most reasons are only one of
the three: an environmental hold is both, a breakdown is neither, and weather
buys days without buying money.

A day is credited when the allowable time on it reaches a share of the hours
logged that day, not when it reaches a fixed number of hours. A six hour shift
rained off entirely lost the whole day; four hours out of six is not two thirds
of nothing.

Days with no shift logged are not credited. There is nothing to credit: the
plant was not there.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from scowbox.errors import FieldError
from scowbox.model.shift import Reason, Shift

DEFAULT_SHARE = 0.5


@dataclass(frozen=True)
class Tally:
    """Hours over a run of shifts, sorted the three ways that matter."""

    shifts: int
    gross_hours: float
    down_hours: float
    allowable_hours: float
    standby_hours: float
    by_reason: tuple[tuple[Reason, float], ...]

    @property
    def effective_hours(self) -> float:
        return round(self.gross_hours - self.down_hours, 2)

    @property
    def contractor_hours(self) -> float:
        """Downtime that buys neither time nor money."""
        return round(self.down_hours - self.allowable_hours, 2)

    @property
    def share_effective(self) -> float:
        if self.gross_hours == 0:
            return 0.0
        return round(self.effective_hours / self.gross_hours, 3)

    def hours_for(self, reason: Reason) -> float:
        for found, hours in self.by_reason:
            if found is reason:
                return hours
        return 0.0


def tally(shifts: Iterable[Shift]) -> Tally:
    """Add up a run of shifts."""
    gathered = list(shifts)
    minutes: dict[Reason, int] = {}
    for shift in gathered:
        for stop in shift.downtimes:
            minutes[stop.reason] = minutes.get(stop.reason, 0) + stop.minutes
    down = sum(minutes.values())
    allowable = sum(m for reason, m in minutes.items() if reason.allowable)
    standby = sum(m for reason, m in minutes.items() if reason.standby)
    return Tally(
        shifts=len(gathered),
        gross_hours=round(sum(s.gross_hours for s in gathered), 2),
        down_hours=round(down / 60, 2),
        allowable_hours=round(allowable / 60, 2),
        standby_hours=round(standby / 60, 2),
        by_reason=tuple(
            (reason, round(minutes[reason] / 60, 2)) for reason in Reason if reason in minutes
        ),
    )


def _by_day(shifts: Sequence[Shift]) -> dict[dt.date, list[Shift]]:
    days: dict[dt.date, list[Shift]] = {}
    for shift in shifts:
        days.setdefault(shift.day, []).append(shift)
    return days


def credited_days(shifts: Iterable[Shift], *, share: float = DEFAULT_SHARE) -> tuple[dt.date, ...]:
    """Days on which allowable downtime reached the share of hours logged."""
    if not 0 < share <= 1:
        raise FieldError("share", "the share of a day that earns a credit is between 0 and 1")
    credited = []
    for day, worked in sorted(_by_day(list(shifts)).items()):
        gross = sum(s.gross_hours for s in worked)
        allowable = sum(
            stop.minutes / 60 for s in worked for stop in s.downtimes if stop.reason.allowable
        )
        if gross > 0 and allowable / gross >= share:
            credited.append(day)
    return tuple(credited)


def extension(shifts: Iterable[Shift], *, share: float = DEFAULT_SHARE) -> int:
    """How many days of contract time the allowable downtime earns back."""
    return len(credited_days(shifts, share=share))


def standby_days(shifts: Iterable[Shift], *, hours_in_day: float = 8.0) -> float:
    """Standby time expressed in day rate days, to the hundredth."""
    if hours_in_day <= 0:
        raise FieldError("hours_in_day", "a standby day is some hours long")
    return round(tally(shifts).standby_hours / hours_in_day, 2)
