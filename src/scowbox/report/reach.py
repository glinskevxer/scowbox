"""The reach report.

One reach, its template, the records that measure it and the quantity those
records come to. Where a reach is measured both ways the two answers sit next
to each other with the spread between them, because that pair of numbers is
the first thing anybody asks about and the last thing a report built around a
single governing figure will show them.
"""

from __future__ import annotations

import sqlite3

from scowbox.boxmeasure.bulking import Bulking
from scowbox.errors import MissingError, RuleError
from scowbox.job.quantities import determine_reach
from scowbox.report.lines import blank, heading, pair, table
from scowbox.store import reaches, surveys, trips

SURVEY_WIDTHS = (10, 12, 10, 14, 10, 10)


def render(
    connection: sqlite3.Connection,
    ident: str,
    bulking: Bulking,
    *,
    deduction: float = 0.0,
) -> list[str]:
    """One reach in full."""
    reach = reaches.get(connection, ident)
    lines = heading(f"Reach {reach.ident}  {reach.name}")
    lines.append(blank())
    lines.append(pair("station", f"{reach.line}  ({reach.length:,.0f} ft)"))
    lines.append(pair("template", reach.template.describe()))
    lines.append(pair("authorized", str(reach.template.authorized_depth)))
    lines.append(pair("required", str(reach.template.required_depth)))
    lines.append(pair("pay", str(reach.template.pay_depth)))
    lines.append(pair("measured by", reach.method.value))
    lines.append(pair("pay group", reach.group))
    lines.append(blank())
    lines.extend(_surveys(connection, ident))
    lines.append(blank())
    lines.extend(_trips(connection, ident))
    lines.append(blank())
    lines.extend(_quantity(connection, ident, bulking, deduction))
    return lines


def _surveys(connection: sqlite3.Connection, ident: str) -> list[str]:
    found = surveys.for_reach(connection, ident)
    if not found:
        return ["No survey of this reach."]
    body = [
        (
            survey.ident,
            survey.taken_on.isoformat(),
            survey.kind.value,
            survey.vessel,
            survey.gauge or "-",
            f"{surveys.full(connection, survey.ident).count:,}",
        )
        for survey in found
    ]
    return table(("survey", "taken", "kind", "vessel", "gauge", "shots"), body, SURVEY_WIDTHS)


def _trips(connection: sqlite3.Connection, ident: str) -> list[str]:
    found = trips.for_reach(connection, ident)
    if not found:
        return ["No scow trip out of this reach."]
    measured = sum(1 for trip in found if trip.measured)
    return [
        pair("trips", f"{len(found):,}"),
        pair("measured", f"{measured:,}"),
        pair("unmeasured", f"{len(found) - measured:,}"),
    ]


def _quantity(
    connection: sqlite3.Connection, ident: str, bulking: Bulking, deduction: float
) -> list[str]:
    try:
        found = determine_reach(connection, ident, bulking, deduction=deduction)
    except (MissingError, RuleError) as trouble:
        return [pair("quantity", f"not measured: {trouble}")]
    lines = [
        pair("survey", found.survey.rounded() if found.survey else "not taken"),
        pair("scow", found.scow.rounded() if found.scow else "not taken"),
    ]
    if found.spread is not None:
        lines.append(pair("spread", f"{found.spread:.1%}"))
    lines.append(pair("governs", found.governs.value))
    lines.append(pair("quantity", found.quantity.rounded()))
    if found.reconcile:
        lines.append(pair("reconcile", "the two measurements do not agree"))
    lines.extend(pair("note", note) for note in found.notes)
    return lines
