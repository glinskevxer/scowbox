"""The windows in force, taken together.

Windows overlap. The entrance can be inside a turtle closure and an oyster
observer window on the same day, and what governs is the strictest of them, not
the first one somebody wrote down. Ties resolve by strictness rank, so the
answer does not depend on the order the book returned the rows in.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable
from dataclasses import dataclass

from scowbox.errors import FieldError
from scowbox.model.window import Restriction, Window


@dataclass(frozen=True)
class Schedule:
    """Every window on the job."""

    windows: tuple[Window, ...]

    @classmethod
    def of(cls, windows: Iterable[Window]) -> Schedule:
        return cls(tuple(windows))

    def in_force(self, day: dt.date, reach: str) -> tuple[Window, ...]:
        """Every window covering a reach on a day, strictest first."""
        found = [w for w in self.windows if w.applies_to(reach) and w.covers(day)]
        return tuple(sorted(found, key=lambda w: (-w.restriction.rank, w.name)))

    def on(self, day: dt.date, reach: str) -> Restriction:
        """What governs a reach on a day."""
        found = self.in_force(day, reach)
        if not found:
            return Restriction.OPEN
        return found[0].restriction

    def closed(self, day: dt.date, reach: str) -> bool:
        return self.on(day, reach).stops_work

    def days_between(
        self, first: dt.date, last: dt.date, reach: str, restriction: Restriction
    ) -> tuple[dt.date, ...]:
        """Every day in a period governed by one restriction."""
        if last < first:
            raise FieldError("last", "a period ends on or after it begins")
        days = []
        day = first
        while day <= last:
            if self.on(day, reach) is restriction:
                days.append(day)
            day += dt.timedelta(days=1)
        return tuple(days)

    def next_open(self, day: dt.date, reach: str, *, within: int = 365) -> dt.date | None:
        """The first day on or after this one that the reach is not closed."""
        for step in range(within + 1):
            candidate = day + dt.timedelta(days=step)
            if not self.closed(candidate, reach):
                return candidate
        return None

    def for_reach(self, reach: str) -> tuple[Window, ...]:
        """Every window that can bind a reach, in date order."""
        found = [w for w in self.windows if w.applies_to(reach)]
        return tuple(sorted(found, key=lambda w: (w.begins, w.name)))
