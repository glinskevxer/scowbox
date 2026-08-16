"""The window report.

The environmental calendar as a planner reads it: over a period, how many days
each reach is open, how many need an observer, and how many are closed
outright. The working days figure is the one that goes in a schedule, and it is
the one nobody can work out by looking at a list of date ranges, because the
ranges overlap and the strictest of them governs.

Weekends are counted as working days here. Whether a contractor works them is a
question about the contractor, not about the permit, and a calendar that
answered it either way would be answering the wrong question.
"""

from __future__ import annotations

import datetime as dt
import sqlite3

from scowbox.errors import FieldError
from scowbox.model.window import Restriction
from scowbox.report.lines import blank, heading, indent, pair, table
from scowbox.store import reaches, windows

WIDTHS = (10, 10, 10, 10, 12, 14)


def render(connection: sqlite3.Connection, first: dt.date, last: dt.date) -> list[str]:
    """Open, restricted and closed days for every reach over a period."""
    if last < first:
        raise FieldError("last", "a period ends on or after it begins")
    schedule = windows.schedule(connection)
    days = (last - first).days + 1
    lines = heading(f"Windows {first} to {last}")
    lines.append(blank())
    lines.append(pair("days", f"{days:,}"))
    lines.append(pair("windows", f"{len(windows.listed(connection)):,}"))
    lines.append(blank())
    held = reaches.listed(connection)
    if not held:
        lines.append("No reach in this book.")
        return lines
    body = []
    for reach in held:
        counted = {
            restriction: len(schedule.days_between(first, last, reach.ident, restriction))
            for restriction in Restriction
        }
        opens = schedule.next_open(first, reach.ident)
        body.append(
            (
                reach.ident,
                f"{counted[Restriction.OPEN]:,}",
                f"{counted[Restriction.OBSERVER]:,}",
                f"{counted[Restriction.CLOSED]:,}",
                f"{counted[Restriction.OPEN] + counted[Restriction.OBSERVER]:,}",
                opens.isoformat() if opens else "not within a year",
            )
        )
    lines.extend(
        table(
            ("reach", "open", "observer", "closed", "workable", "next open"),
            body,
            WIDTHS,
        )
    )
    lines.append(blank())
    lines.extend(_in_force(connection, first, last))
    return lines


def _in_force(connection: sqlite3.Connection, first: dt.date, last: dt.date) -> list[str]:
    """Every window that touches the period at all."""
    found = [
        window
        for window in windows.listed(connection)
        if window.begins <= last and window.ends >= first
    ]
    if not found:
        return ["No window touches this period."]
    return [
        f"{len(found):,} windows touch this period",
        *indent(window.describe() for window in found),
    ]
