"""One environmental window."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from enum import Enum

from scowbox.errors import FieldError
from scowbox.ids import is_ident

ALL_REACHES = ""


class Restriction(Enum):
    """What a window does while it is open."""

    OPEN = "open"
    OBSERVER = "observer required"
    CLOSED = "closed"

    @property
    def rank(self) -> int:
        """Strictness, so that overlapping windows resolve the same way twice."""
        return {Restriction.OPEN: 0, Restriction.OBSERVER: 1, Restriction.CLOSED: 2}[self]

    @property
    def stops_work(self) -> bool:
        return self is Restriction.CLOSED


@dataclass(frozen=True)
class Window:
    """A date range in which one reach, or the whole job, is restricted."""

    name: str
    begins: dt.date
    ends: dt.date
    restriction: Restriction
    authority: str
    reach: str = ALL_REACHES

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise FieldError("name", "a window is named for what it protects")
        if not self.authority.strip():
            raise FieldError("authority", "a window comes from somebody")
        if self.ends < self.begins:
            raise FieldError("ends", "a window ends on or after it begins")
        if self.reach != ALL_REACHES and not is_ident("reach", self.reach):
            raise FieldError("reach", f"{self.reach!r} is not a reach identifier")

    @property
    def whole_job(self) -> bool:
        return self.reach == ALL_REACHES

    @property
    def days(self) -> int:
        """Length of the window in days, both ends included."""
        return (self.ends - self.begins).days + 1

    def covers(self, day: dt.date) -> bool:
        return self.begins <= day <= self.ends

    def applies_to(self, reach: str) -> bool:
        return self.whole_job or self.reach == reach

    def describe(self) -> str:
        where = "all reaches" if self.whole_job else self.reach
        return (
            f"{self.name} ({self.authority}): {self.begins} to {self.ends},"
            f" {where}, {self.restriction.value}"
        )
