"""The audit report.

The compliance sweep, rendered. Violations first, then warnings, then notes,
with a count at the top so a reader who is only checking whether anything is
wrong does not have to read the whole thing to find out.
"""

from __future__ import annotations

import datetime as dt
import sqlite3

from scowbox.compliance.findings import Severity, counted
from scowbox.job.sweeping import gather
from scowbox.report.lines import blank, heading, indent, pair


def render(connection: sqlite3.Connection, closed_through: dt.date | None = None) -> list[str]:
    """The sweep as a page."""
    found = gather(connection, closed_through)
    lines = heading("Audit")
    lines.append(blank())
    lines.append(pair("shifts", f"{found.shifts:,}"))
    lines.append(pair("trips", f"{found.trips:,}"))
    lines.append(pair("tickets", f"{found.tickets:,}"))
    lines.append(blank())
    if found.clean:
        lines.append("Nothing outstanding.")
        return lines
    tally = counted(found.findings)
    lines.append(
        f"{tally[Severity.VIOLATION]} violations,"
        f" {tally[Severity.WARNING]} warnings,"
        f" {tally[Severity.NOTE]} notes"
    )
    lines.append(blank())
    lines.extend(indent(finding.line() for finding in found.findings))
    return lines
