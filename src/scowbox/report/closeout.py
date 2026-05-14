"""The closeout report.

The list somebody works through in the last month, in the order they would work
through it: what cannot be measured, what cannot be reduced, what left without
a ticket, what is in dispute, and what the sweep is still holding.
"""

from __future__ import annotations

import datetime as dt
import sqlite3

from scowbox.boxmeasure.bulking import Bulking
from scowbox.job.season import Closeout, closeout
from scowbox.report.lines import blank, heading, indent, pair


def render(
    connection: sqlite3.Connection,
    bulking: Bulking,
    *,
    closed_through: dt.date | None = None,
) -> list[str]:
    """Everything standing between the job and a final estimate."""
    found = closeout(connection, bulking, closed_through=closed_through)
    lines = heading("Closeout")
    lines.append(blank())
    lines.append(pair("outstanding", f"{found.outstanding:,}"))
    lines.append(pair("estimates", f"{found.estimates:,}"))
    lines.append(pair("final", "written" if found.closed else "not written"))
    lines.append(blank())
    lines.extend(_section("Reaches nobody can measure", found.unmeasured))
    lines.extend(_section("Surveys nobody can reduce", found.unreduced))
    lines.extend(_flat("Trips with no placement ticket", found.unticketed))
    lines.extend(_flat("Reaches in dispute", found.disputed))
    lines.append(pair("violations", f"{found.violations:,}"))
    lines.append(pair("warnings", f"{found.warnings:,}"))
    lines.append(blank())
    lines.append(_verdict(found))
    return lines


def _section(title: str, items: tuple[tuple[str, str], ...]) -> list[str]:
    if not items:
        return [f"{title}: none", ""]
    return [
        f"{title}: {len(items):,}",
        *indent(f"{ident}  {why}" for ident, why in items),
        "",
    ]


def _flat(title: str, items: tuple[str, ...]) -> list[str]:
    if not items:
        return [f"{title}: none", ""]
    return [f"{title}: {len(items):,}", *indent(items), ""]


def _verdict(found: Closeout) -> str:
    if found.closed:
        return "The final estimate is written. This contract is closed."
    if found.closeable:
        return "Nothing outstanding. The final estimate can be written."
    return f"{found.outstanding:,} things stand in the way of a final estimate."
