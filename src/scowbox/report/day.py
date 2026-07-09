"""The day report.

One day, everything that happened on it, and everything about it that is not
right yet. It is the report the project engineer reads in the morning, so what
is wrong goes at the bottom where the eye stops rather than in a section
somebody has to remember to look at.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Mapping, Sequence

from scowbox.boxmeasure.box import measure
from scowbox.compliance.findings import Severity, counted
from scowbox.compliance.sweep import sweep
from scowbox.errors import MissingError, RuleError
from scowbox.measure.placing import standing
from scowbox.model.scow import Scow, ScowTrip
from scowbox.model.shift import Shift
from scowbox.pay.timeloss import tally
from scowbox.report.lines import blank, heading, indent, pair, table
from scowbox.store import placements, scows, shifts, trips, windows

SHIFT_WIDTHS = (10, 9, 9, 8, 10, 10)
TRIP_WIDTHS = (10, 8, 10, 12, 22, 12)


def render(connection: sqlite3.Connection, day: dt.date) -> list[str]:
    """Everything the book holds about one day."""
    worked = [s for s in shifts.between(connection, day, day) if s.day == day]
    loads = trips.between(connection, day, day)
    lines = heading(f"Day report {day:%Y-%m-%d}")
    lines.append(blank())
    lines.extend(_shifts(worked))
    lines.append(blank())
    lines.extend(_trips(connection, loads))
    lines.append(blank())
    lines.extend(_placed(connection, day))
    lines.append(blank())
    lines.extend(_findings(connection, day, worked, loads))
    return lines


def _placed(connection: sqlite3.Connection, day: dt.date) -> list[str]:
    """Where the day's loads went, and what each area holds now.

    Against the whole record rather than the day, because the number somebody
    wants off this line is how much room is left in the cell, not how much went
    into it this morning.
    """
    areas = placements.listed(connection)
    if not areas:
        return ["No placement area in this book."]
    lines = []
    for area in areas:
        held = trips.tickets_for_area(connection, area.ident)
        today = [t for t in held if t.released.date() == day]
        if not today:
            continue
        total = standing(area, held)
        room = "open" if total.remaining is None else f"{total.remaining} left"
        lines.append(pair(area.ident, f"{len(today):,} loads today, {total.placed} placed, {room}"))
    return lines or ["Nothing placed on this day."]


def _shifts(worked: Sequence[Shift]) -> list[str]:
    if not worked:
        return ["No shift logged."]
    got = tally(worked)
    body = [
        (
            shift.ident,
            shift.dredge,
            shift.reach,
            f"{shift.gross_hours:.1f}",
            f"{shift.effective_hours:.1f}",
            f"{shift.down_minutes / 60:.1f}",
        )
        for shift in worked
    ]
    lines = table(("shift", "dredge", "reach", "gross", "effective", "down"), body, SHIFT_WIDTHS)
    lines.append(blank())
    lines.append(pair("effective", f"{got.effective_hours:.2f} of {got.gross_hours:.2f} hours"))
    lines.append(pair("allowable", f"{got.allowable_hours:.2f} hours"))
    lines.append(pair("contractor", f"{got.contractor_hours:.2f} hours"))
    return lines


def _trips(connection: sqlite3.Connection, loads: Sequence[ScowTrip]) -> list[str]:
    if not loads:
        return ["No scow trip logged."]
    fleet = {scow.ident: scow for scow in scows.listed(connection)}
    body = []
    for trip in loads:
        yards, state = _box(fleet, trip)
        try:
            ticket = trips.ticket_of(connection, trip.ident)
            where = ticket.area
        except MissingError:
            where = "no ticket"
        body.append((trip.ident, trip.scow, trip.reach, yards, state, where))
    return table(("trip", "scow", "reach", "scow yards", "box", "placed"), body, TRIP_WIDTHS)


def _box(fleet: Mapping[str, Scow], trip: ScowTrip) -> tuple[str, str]:
    """A trip's yards and the state of its box, however wrong the box is.

    A day report that raised because one scow was struck off the fleet, or
    because one crew measured down from the wrong reference, took the whole
    day's work off the page with it. Neither is a reason not to print the other
    eleven trips, so both come back as a state in the box column and the trip
    keeps its row. What is wrong with the box in detail is a question for
    ``scowbox trip show``.
    """
    if not trip.measured:
        return "-", "unmeasured"
    scow = fleet.get(trip.scow)
    if scow is None:
        return "-", "scow struck off"
    try:
        got = measure(scow, trip)
    except RuleError:
        return "-", "box unusable"
    if got.sound:
        return got.scow_yards.rounded(), "measured"
    return got.scow_yards.rounded(), ", ".join(got.suspect)


def _findings(
    connection: sqlite3.Connection,
    day: dt.date,
    worked: Sequence[Shift],
    loads: Sequence[ScowTrip],
) -> list[str]:
    areas = {area.ident: area for area in placements.listed(connection)}
    tickets = [
        ticket
        for area in areas
        for ticket in trips.tickets_for_area(connection, area)
        if ticket.released.date() == day
    ]
    found = sweep(worked, loads, tickets, areas, windows.schedule(connection))
    if found.clean:
        return ["Nothing outstanding."]
    tally_by = counted(found.findings)
    lines = [
        f"{tally_by[Severity.VIOLATION]} violations,"
        f" {tally_by[Severity.WARNING]} warnings,"
        f" {tally_by[Severity.NOTE]} notes"
    ]
    lines.extend(indent(finding.line() for finding in found.findings))
    return lines
