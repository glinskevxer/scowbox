"""The sweep.

Three questions, asked of the records that are there rather than of the ones
that ought to be. Was work done inside a closure. Did a load go somewhere that
takes it. Does every trip that left have a ticket saying where it ended up.

The severity of each answer is fixed here and not argued about in the report. A
shift inside a closed window is a violation whatever its length. Working inside
an observer window is a warning, because whether an observer was aboard is not
something the shift log records and somebody has to go and look. A trip with no
ticket is a warning until the month closes and a violation after it, and the
sweep is told which by being given the day the month closed.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from scowbox.compliance.findings import Finding, Severity, ordered
from scowbox.measure.placing import standing
from scowbox.model.placement import PlacementArea, PlacementTicket
from scowbox.model.scow import ScowTrip
from scowbox.model.shift import Shift
from scowbox.model.window import Restriction
from scowbox.windows.schedule import Schedule


@dataclass(frozen=True)
class Sweep:
    """Everything one pass over the records turned up."""

    findings: tuple[Finding, ...]
    shifts: int
    trips: int
    tickets: int

    @property
    def clean(self) -> bool:
        return not self.findings


def shifts_against_windows(shifts: Iterable[Shift], schedule: Schedule) -> tuple[Finding, ...]:
    """Shifts worked inside a window that restricted the reach."""
    found = []
    for shift in shifts:
        governs = schedule.on(shift.day, shift.reach)
        if governs is Restriction.OPEN:
            continue
        binding = schedule.in_force(shift.day, shift.reach)[0]
        severity = Severity.VIOLATION if governs is Restriction.CLOSED else Severity.WARNING
        found.append(
            Finding(
                kind="window",
                subject=shift.ident,
                day=shift.day,
                severity=severity,
                detail=(
                    f"{shift.reach} worked while {binding.name} was in force"
                    f" ({binding.restriction.value}, {binding.authority})"
                ),
            )
        )
    return tuple(found)


def tickets_against_areas(
    tickets: Iterable[PlacementTicket], areas: Mapping[str, PlacementArea]
) -> tuple[Finding, ...]:
    """Loads placed where the ground does not take them, or past a capacity."""
    held = list(tickets)
    found = []
    for ticket in held:
        area = areas.get(ticket.area)
        if area is None:
            found.append(
                Finding(
                    kind="placement",
                    subject=ticket.trip,
                    day=ticket.released.date(),
                    severity=Severity.VIOLATION,
                    detail=f"released at {ticket.area}, which is not a placement area",
                )
            )
            continue
        if not area.takes(ticket.grade):
            found.append(
                Finding(
                    kind="placement",
                    subject=ticket.trip,
                    day=ticket.released.date(),
                    severity=Severity.VIOLATION,
                    detail=(
                        f"{ticket.grade.value} material at {area.ident},"
                        f" a {area.ground.value} under permit {area.permit}"
                    ),
                )
            )
    for area in areas.values():
        total = standing(area, held)
        if total.full:
            found.append(
                Finding(
                    kind="capacity",
                    subject=area.ident,
                    day=max(
                        (t.released.date() for t in held if t.area == area.ident),
                        default=dt.date.min,
                    ),
                    severity=Severity.WARNING,
                    detail=f"{area.name} is at capacity under permit {area.permit}",
                )
            )
    return tuple(found)


def trips_without_tickets(
    trips: Iterable[ScowTrip], ticketed: Iterable[str], closed_through: dt.date | None = None
) -> tuple[Finding, ...]:
    """Trips that left with no record of where they ended up."""
    have = set(ticketed)
    found = []
    for trip in trips:
        if trip.ident in have:
            continue
        past_close = closed_through is not None and trip.loaded_on <= closed_through
        found.append(
            Finding(
                kind="ticket",
                subject=trip.ident,
                day=trip.loaded_on,
                severity=Severity.VIOLATION if past_close else Severity.WARNING,
                detail=f"loaded out of {trip.reach} with no placement ticket",
            )
        )
    return tuple(found)


def sweep(
    shifts: Iterable[Shift],
    trips: Iterable[ScowTrip],
    tickets: Iterable[PlacementTicket],
    areas: Mapping[str, PlacementArea],
    schedule: Schedule,
    *,
    closed_through: dt.date | None = None,
) -> Sweep:
    """Run every check over one period's records."""
    held_shifts = list(shifts)
    held_trips = list(trips)
    held_tickets = list(tickets)
    findings = [
        *shifts_against_windows(held_shifts, schedule),
        *tickets_against_areas(held_tickets, areas),
        *trips_without_tickets(held_trips, (t.trip for t in held_tickets), closed_through),
    ]
    return Sweep(
        findings=ordered(findings),
        shifts=len(held_shifts),
        trips=len(held_trips),
        tickets=len(held_tickets),
    )
