"""Tide gauge records.

The gauge publishes a height above datum every six minutes. A sounding taken
between two publications is reduced with the tide interpolated between them,
straight line, which is what the survey manual says and what the survey
software does.

Two things this refuses to do. It will not extrapolate past the ends of the
record, because a sounding taken before the gauge was reading has no tide and
guessing one is how a whole day's work ends up half a foot out. And it will not
interpolate across a gap wider than the allowed one: a gauge that dropped out
for two hours did not record the tide during those two hours, whatever a
straight line between its last reading and its next one suggests.
"""

from __future__ import annotations

import datetime as dt
from bisect import bisect_left
from dataclasses import dataclass

from scowbox.errors import FieldError, MissingError, RuleError
from scowbox.units.clock import aware

MAX_GAP_MINUTES = 30
"""Widest gap the record will interpolate across."""

MAX_HEIGHT_FEET = 20.0


@dataclass(frozen=True)
class TideReading:
    """One published height above datum."""

    at: dt.datetime
    height: float

    def __post_init__(self) -> None:
        aware(self.at)
        if abs(self.height) > MAX_HEIGHT_FEET:
            raise FieldError("height", f"{self.height:g} ft is not a tide on this coast")


@dataclass(frozen=True)
class TideRecord:
    """Everything one gauge published over the period of a survey."""

    gauge: str
    readings: tuple[TideReading, ...]

    def __post_init__(self) -> None:
        if not self.gauge.strip():
            raise FieldError("gauge", "a tide record names its gauge")
        if not self.readings:
            raise FieldError("readings", "a tide record with no readings reduces nothing")
        for earlier, later in zip(self.readings, self.readings[1:], strict=False):
            if later.at <= earlier.at:
                raise FieldError("readings", "tide readings are in time order and distinct")

    @property
    def begins(self) -> dt.datetime:
        return self.readings[0].at

    @property
    def ends(self) -> dt.datetime:
        return self.readings[-1].at

    def covers(self, when: dt.datetime) -> bool:
        """True when the moment lies inside the published period."""
        return self.begins <= aware(when) <= self.ends

    def height_at(self, when: dt.datetime) -> float:
        """Tide height above datum at a moment, interpolated between readings."""
        aware(when)
        if not self.covers(when):
            raise MissingError("tide reading at", when.isoformat())
        times = [r.at for r in self.readings]
        index = bisect_left(times, when)
        if times[index] == when:
            return self.readings[index].height
        before, after = self.readings[index - 1], self.readings[index]
        span = (after.at - before.at).total_seconds() / 60
        if span > MAX_GAP_MINUTES:
            raise RuleError(
                f"gauge {self.gauge} has a {span:.0f} minute gap over {when.isoformat()}"
            )
        share = (when - before.at).total_seconds() / 60 / span
        return round(before.height + (after.height - before.height) * share, 3)

    def gaps(self) -> tuple[tuple[dt.datetime, dt.datetime], ...]:
        """Every stretch the record cannot be interpolated across."""
        found = []
        for before, after in zip(self.readings, self.readings[1:], strict=False):
            if (after.at - before.at).total_seconds() / 60 > MAX_GAP_MINUTES:
                found.append((before.at, after.at))
        return tuple(found)
