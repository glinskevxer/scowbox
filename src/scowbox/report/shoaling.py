"""The shoaling report.

One line a reach, over the most recent interval nobody dredged it. A reach with
no such interval is named rather than left off, because a channel that has been
worked continuously for two years is exactly the one somebody will want a rate
for and exactly the one that cannot have it.
"""

from __future__ import annotations

import sqlite3

from scowbox.errors import MissingError, RuleError
from scowbox.job.history import latest_shoaling, quiet_pairs
from scowbox.measure.shoaling import MIN_SPAN_DAYS
from scowbox.report.lines import blank, heading, pair, table
from scowbox.store import reaches

WIDTHS = (10, 12, 12, 8, 16, 16)


def render(connection: sqlite3.Connection, *, min_days: int = MIN_SPAN_DAYS) -> list[str]:
    """Shoaling rates over the whole channel."""
    lines = heading("Shoaling")
    lines.append(blank())
    lines.append(pair("interval", f"at least {min_days} days with no shift on the reach"))
    lines.append(blank())
    body = []
    quiet = []
    for reach in reaches.listed(connection):
        try:
            found = latest_shoaling(connection, reach.ident, min_days=min_days)
        except (MissingError, RuleError) as trouble:
            quiet.append(f"{reach.ident}  {trouble}")
            continue
        body.append(
            (
                found.reach,
                found.earlier,
                found.later,
                f"{found.days:,}",
                found.gained.rounded(),
                f"{found.yards_a_year:,.0f} cy a year",
            )
        )
    if body:
        lines.extend(table(("reach", "earlier", "later", "days", "gained", "rate"), body, WIDTHS))
    else:
        lines.append("No reach has a quiet interval to measure over.")
    if quiet:
        lines.append(blank())
        lines.extend(quiet)
    return lines


def intervals(connection: sqlite3.Connection, reach: str) -> list[str]:
    """Every quiet interval on one reach, oldest first."""
    pairs = quiet_pairs(connection, reach)
    if not pairs:
        return [f"{reach} has no interval nobody dredged it in."]
    return [
        f"{earlier.ident} to {later.ident}:"
        f" {(later.taken_on - earlier.taken_on).days:,} days"
        f" from {earlier.taken_on} to {later.taken_on}"
        for earlier, later in pairs
    ]
