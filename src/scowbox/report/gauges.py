"""The gauge report.

Which gauges the book holds, what they cover, where they dropped out, and which
surveys cannot be reduced because of it.

The last of those is the one worth printing. A gauge with a two hour gap in it
is a curiosity until a survey was run during those two hours, and then it is a
day of vessel time nobody can bill against.
"""

from __future__ import annotations

import sqlite3

from scowbox.errors import MissingError, RuleError
from scowbox.job.quantities import tide_for
from scowbox.report.lines import blank, heading, indent, pair, table
from scowbox.store import surveys, tides

WIDTHS = (12, 20, 20, 10)


def render(connection: sqlite3.Connection) -> list[str]:
    """Every gauge, what it covers and what depends on it."""
    lines = heading("Gauges")
    lines.append(blank())
    held = tides.gauges(connection)
    if not held:
        lines.append("No gauge readings in this book.")
    else:
        lines.extend(_gauges(connection, held))
        lines.append(blank())
        lines.extend(_gaps(connection, held))
    lines.append(blank())
    lines.extend(_surveys(connection))
    return lines


def _gauges(connection: sqlite3.Connection, held: tuple[str, ...]) -> list[str]:
    body = []
    for gauge in held:
        first, last = tides.span(connection, gauge)
        wanted = [s.ident for s in surveys.listed(connection) if s.gauge == gauge]
        body.append(
            (
                gauge,
                f"{first:%Y-%m-%d %H:%M}",
                f"{last:%Y-%m-%d %H:%M}",
                f"{len(wanted):,}",
            )
        )
    return table(("gauge", "from", "to", "surveys"), body, WIDTHS)


def _gaps(connection: sqlite3.Connection, held: tuple[str, ...]) -> list[str]:
    lines = []
    for gauge in held:
        first, last = tides.span(connection, gauge)
        record = tides.record_for(connection, gauge, first, last)
        found = record.gaps()
        if not found:
            continue
        lines.append(f"{gauge}: {len(found):,} gaps too wide to interpolate across")
        lines.extend(
            indent(
                f"{began:%Y-%m-%d %H:%M} to {ended:%Y-%m-%d %H:%M}"
                f" ({(ended - began).total_seconds() / 60:,.0f} minutes)"
                for began, ended in found
            )
        )
    return lines or ["No gauge has a gap in it."]


def _surveys(connection: sqlite3.Connection) -> list[str]:
    trouble = []
    for survey in surveys.listed(connection):
        try:
            tide_for(connection, survey)
        except (MissingError, RuleError) as why:
            trouble.append(f"{survey.ident} ({survey.taken_on}): {why}")
    if not trouble:
        return ["Every survey in the book can be reduced."]
    return [
        pair("cannot reduce", f"{len(trouble):,} surveys"),
        *indent(trouble),
    ]
