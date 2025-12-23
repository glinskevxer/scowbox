"""The production report.

Day by day, what was moved and what it took. The averages at the bottom are
over the whole period rather than the mean of the daily figures, because a day
with one effective hour on it would otherwise weigh as much as a full shift.
"""

from __future__ import annotations

import sqlite3

from scowbox.boxmeasure.bulking import Bulking
from scowbox.errors import MissingError, RuleError
from scowbox.job.quantities import determine_reach
from scowbox.job.rates import average_load, daily, for_reach
from scowbox.measure.production import best, worst
from scowbox.report.lines import blank, heading, pair, table
from scowbox.store import reaches

DAY_WIDTHS = (12, 9, 8, 14, 14, 14)


def render(
    connection: sqlite3.Connection, bulking: Bulking, *, reach: str | None = None
) -> list[str]:
    """Production over the job, or over one reach."""
    title = "Production" if reach is None else f"Production, {reach}"
    lines = heading(title)
    lines.append(blank())
    lines.append(pair("average load", average_load(connection, reach).rounded()))
    lines.append(blank())
    lines.extend(_days(connection, reach))
    lines.append(blank())
    lines.extend(_reaches(connection, bulking, reach))
    return lines


def _days(connection: sqlite3.Connection, reach: str | None) -> list[str]:
    rates = daily(connection, reach)
    if not rates:
        return ["No shift or trip logged."]
    body = [
        (
            day.isoformat(),
            f"{rate.hours:.2f}",
            f"{rate.trips:,}",
            rate.yards.rounded(),
            _or_dash(rate.yards_per_hour),
            _or_dash(rate.minutes_per_trip),
        )
        for day, rate in rates
    ]
    lines = table(
        ("day", "hours", "trips", "yards", "cy per hour", "min per trip"), body, DAY_WIDTHS
    )
    top = best(rates)
    bottom = worst(rates)
    if top is not None and bottom is not None:
        lines.append(blank())
        lines.append(pair("best day", f"{top[0]} at {_or_dash(top[1].yards_per_hour)} cy an hour"))
        lines.append(
            pair("worst day", f"{bottom[0]} at {_or_dash(bottom[1].yards_per_hour)} cy an hour")
        )
    return lines


def _reaches(connection: sqlite3.Connection, bulking: Bulking, only: str | None) -> list[str]:
    wanted = [r for r in reaches.listed(connection) if only is None or r.ident == only]
    lines = []
    for reach in wanted:
        try:
            found = determine_reach(connection, reach.ident, bulking)
        except (MissingError, RuleError):
            lines.append(pair(reach.ident, "not measured"))
            continue
        rate = for_reach(connection, reach.ident, found.quantity)
        lines.append(
            pair(
                reach.ident,
                f"{found.quantity.rounded()} over {rate.hours:.2f} hours,"
                f" {_or_dash(rate.yards_per_hour)} cy an hour",
            )
        )
    return lines or ["No reach in the book."]


def _or_dash(value: float | None) -> str:
    return "-" if value is None else f"{value:,.1f}"
