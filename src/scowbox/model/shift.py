"""Shift logs.

The dredge tender writes one of these every shift: when work started, when it
stopped, and every interruption in between with a reason against it. The
reasons are a fixed list because two of the things hanging off them are
contractual. Allowable downtime earns a day back on contract time. Standby
downtime is paid at the day rate. A reason invented in the field is a reason
nobody agreed the treatment of.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from enum import Enum
from itertools import pairwise

from scowbox.errors import FieldError
from scowbox.ids import is_ident
from scowbox.units.clock import aware, hours_between, minutes_between


class Reason(Enum):
    """Why the dredge was not dredging."""

    WEATHER = "weather"
    TRAFFIC = "channel traffic"
    ENVIRONMENTAL = "environmental hold"
    BREAKDOWN = "breakdown"
    CREW = "crew"
    PIPELINE = "pipeline move"
    HOLIDAY = "holiday"
    NO_WORK = "no work scheduled"

    @property
    def allowable(self) -> bool:
        """True when the time comes back as an extension of contract time."""
        return self in (Reason.WEATHER, Reason.TRAFFIC, Reason.ENVIRONMENTAL)

    @property
    def standby(self) -> bool:
        """True when the time is paid at the standby rate."""
        return self in (Reason.TRAFFIC, Reason.ENVIRONMENTAL)


@dataclass(frozen=True)
class Downtime:
    """One interruption inside a shift."""

    began: dt.datetime
    ended: dt.datetime
    reason: Reason
    note: str = ""

    def __post_init__(self) -> None:
        aware(self.began)
        aware(self.ended)
        if self.ended <= self.began:
            raise FieldError("ended", "an interruption ends after it begins")

    @property
    def minutes(self) -> int:
        return minutes_between(self.began, self.ended)

    @property
    def hours(self) -> float:
        return hours_between(self.began, self.ended)


@dataclass(frozen=True)
class Shift:
    """One shift of one dredge on one reach."""

    ident: str
    dredge: str
    reach: str
    began: dt.datetime
    ended: dt.datetime
    downtimes: tuple[Downtime, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not is_ident("shift", self.ident):
            raise FieldError("ident", f"{self.ident!r} is not a shift identifier")
        if not is_ident("plant", self.dredge):
            raise FieldError("dredge", f"{self.dredge!r} is not a plant identifier")
        if not is_ident("reach", self.reach):
            raise FieldError("reach", f"{self.reach!r} is not a reach identifier")
        aware(self.began)
        aware(self.ended)
        if self.ended <= self.began:
            raise FieldError("ended", "a shift ends after it begins")
        for stop in self.downtimes:
            if stop.began < self.began or stop.ended > self.ended:
                raise FieldError("downtimes", f"an interruption falls outside {self.ident}")
        ordered = sorted(self.downtimes, key=lambda d: d.began)
        for earlier, later in pairwise(ordered):
            if later.began < earlier.ended:
                raise FieldError("downtimes", f"two interruptions overlap in {self.ident}")

    @property
    def day(self) -> dt.date:
        """The day the shift is logged against, which is the day it started."""
        return self.began.date()

    @property
    def gross_hours(self) -> float:
        return hours_between(self.began, self.ended)

    @property
    def down_minutes(self) -> int:
        return sum(stop.minutes for stop in self.downtimes)

    @property
    def effective_hours(self) -> float:
        """Hours actually dredging."""
        return round(minutes_between(self.began, self.ended) / 60 - self.down_minutes / 60, 2)

    def stopped_for(self, reason: Reason) -> int:
        """Minutes lost to one reason."""
        return sum(stop.minutes for stop in self.downtimes if stop.reason is reason)
