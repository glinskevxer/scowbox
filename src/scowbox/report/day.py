"""The day report.

One day, everything that happened on it, and everything about it that is not
right yet. It is the report the project engineer reads in the morning, so what
is wrong goes at the bottom where the eye stops rather than in a section
somebody has to remember to look at.
"""

from __future__ import annotations

import datetime as dt
import sqlite3

from scowbox.boxmeasure.box import measure
from scowbox.compliance.findings import Severity, counted
from scowbox.compliance.sweep import sweep
from scowbox.errors import MissingError
from scowbox.pay.timeloss import tally
from scowbox.report.lines import blank, heading, indent, pair, table
from scowbox.store import placements, scows, shifts, trips, windows

SHIFT_WIDTHS = (10, 9, 9, 8, 10, 10)
TRIP_WIDTHS = (10, 8, 10, 12, 12, 14)


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
    lines.extend(_findings(connection, day, worked, loads))
    return lines


def _shifts(worked: list) -> list[str]:  # type: ignore[type-arg]
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


def _trips(connection: sqlite3.Connection, loads: tuple) -> list[str]:  # type: ignore[type-arg]
    if not loads:
        return ["No scow trip logged."]
    body = []
    for trip in loads:
        if trip.measured:
            got = measure(scows.get(connection, trip.scow), trip)
            yards = got.scow_yards.rounded()
            state = "suspect" if not got.sound else "measured"
        else:
            yards = "-"
            state = "unmeasured"
        try:
            ticket = trips.ticket_of(connection, trip.ident)
            where = ticket.area
        except MissingError:
            where = "no ticket"
        body.append((trip.ident, trip.scow, trip.reach, yards, state, where))
    return table(("trip", "scow", "reach", "scow yards", "box", "placed"), body, TRIP_WIDTHS)


def _findings(
    connection: sqlite3.Connection,
    day: dt.date,
    worked: list,  # type: ignore[type-arg]
    loads: tuple,  # type: ignore[type-arg]
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
