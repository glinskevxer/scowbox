"""Reading a shift log and a trip sheet against each other before either lands.

Both feed parsers check themselves. Neither has ever been checked against the
other, and the disagreements between them are the ones worth catching: a trip
sheet naming a day the log has no shift on, a mechanical dredge that worked a
shift and brought nothing back, a reach or a scow the book has never heard of.

All three are cheap to fix while the files are still on somebody's desk and
expensive afterwards, because loading them writes rows that other rows then
point at.

`Plant.loads_scows` is the predicate the second check turns on, and this is the
first rule to ask it. A cutter suction dredge pumps ashore through a pipeline
and a shift with no scow trips against it is an ordinary day; the same shift on
a mechanical dredge is a gap.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from scowbox.compliance.findings import Finding, Severity, ordered
from scowbox.model.scow import ScowTrip
from scowbox.model.shift import Shift
from scowbox.store import placements, reaches, scows, shifts


@dataclass(frozen=True)
class Preflight:
    """What reading the two files together turned up."""

    findings: tuple[Finding, ...]
    shifts: int
    trips: int

    @property
    def clean(self) -> bool:
        return not self.findings

    @property
    def blocking(self) -> tuple[Finding, ...]:
        """Findings that name something the book does not hold."""
        return tuple(f for f in self.findings if f.severity is Severity.VIOLATION)


@dataclass(frozen=True)
class Held:
    """What the book already knows about, for the existence checks."""

    reaches: frozenset[str]
    scows: frozenset[str]
    areas: frozenset[str]
    dredges: frozenset[str]


def held_by(connection: sqlite3.Connection) -> Held:
    """Every identifier the book can already resolve."""
    return Held(
        reaches=frozenset(r.ident for r in reaches.listed(connection)),
        scows=frozenset(s.ident for s in scows.listed(connection)),
        areas=frozenset(a.ident for a in placements.listed(connection)),
        dredges=frozenset(d.ident for d in shifts.dredges(connection)),
    )


def loads_scows(connection: sqlite3.Connection) -> frozenset[str]:
    """The dredges whose shifts are expected to produce scow trips."""
    return frozenset(d.ident for d in shifts.dredges(connection) if d.plant.loads_scows)


def unknown(worked: Sequence[Shift], hauled: Sequence[ScowTrip], held: Held) -> list[Finding]:
    """Every record naming something the book does not hold."""
    found = []
    for shift in worked:
        for label, ident, known in (
            ("reach", shift.reach, held.reaches),
            ("dredge", shift.dredge, held.dredges),
        ):
            if ident not in known:
                found.append(
                    Finding(
                        kind=f"unknown {label}",
                        subject=shift.ident,
                        day=shift.day,
                        severity=Severity.VIOLATION,
                        detail=f"names {label} {ident}, which the book does not hold",
                    )
                )
    for trip in hauled:
        for label, ident, known in (
            ("reach", trip.reach, held.reaches),
            ("scow", trip.scow, held.scows),
            ("placement area", trip.placement, held.areas),
        ):
            if ident not in known:
                found.append(
                    Finding(
                        kind=f"unknown {label}",
                        subject=trip.ident,
                        day=trip.loaded_on,
                        severity=Severity.VIOLATION,
                        detail=f"names {label} {ident}, which the book does not hold",
                    )
                )
    return found


def unworked(worked: Sequence[Shift], hauled: Sequence[ScowTrip]) -> list[Finding]:
    """Trips loaded on a day and a reach the log has no shift for."""
    days = {(shift.reach, shift.day) for shift in worked}
    return [
        Finding(
            kind="no shift",
            subject=trip.ident,
            day=trip.loaded_on,
            severity=Severity.WARNING,
            detail=f"loaded out of {trip.reach} on a day the log has no shift for",
        )
        for trip in hauled
        if (trip.reach, trip.loaded_on) not in days
    ]


def unhauled(
    worked: Sequence[Shift], hauled: Sequence[ScowTrip], mechanical: frozenset[str]
) -> list[Finding]:
    """Shifts by a scow loading dredge that brought nothing back."""
    days: set[tuple[str, dt.date]] = {(t.reach, t.loaded_on) for t in hauled}
    return [
        Finding(
            kind="no trip",
            subject=shift.ident,
            day=shift.day,
            severity=Severity.WARNING,
            detail=f"{shift.dredge} loads scows and the sheet has no trip against it",
        )
        for shift in worked
        if shift.dredge in mechanical and (shift.reach, shift.day) not in days
    ]


def preflight(
    connection: sqlite3.Connection,
    worked: Iterable[Shift],
    hauled: Iterable[ScowTrip],
) -> Preflight:
    """Read a parsed shift log and trip sheet against each other and the book."""
    log = list(worked)
    sheet = list(hauled)
    found = [
        *unknown(log, sheet, held_by(connection)),
        *unworked(log, sheet),
        *unhauled(log, sheet, loads_scows(connection)),
    ]
    return Preflight(findings=ordered(found), shifts=len(log), trips=len(sheet))
