"""The season report.

Where the job stands: what is in the book, what has been measured, what has
been billed and what is still outstanding. It is the page that goes in front of
the monthly estimate, so every figure on it is one somebody may be asked about
in the same meeting.
"""

from __future__ import annotations

import sqlite3

from scowbox.boxmeasure.bulking import Bulking
from scowbox.job.quantities import by_group, measured_through, unmeasured
from scowbox.pay.timeloss import extension, tally
from scowbox.report.lines import blank, heading, indent, pair, table
from scowbox.store import contracts, estimates, reaches, shifts, surveys, trips
from scowbox.units.money import Money
from scowbox.units.volume import total

GROUP_WIDTHS = (16, 16, 16, 14)
ESTIMATE_WIDTHS = (10, 12, 18, 18)


def render(
    connection: sqlite3.Connection, bulking: Bulking, *, deduction: float = 0.0
) -> list[str]:
    """Where the job stands today."""
    lines = heading("Season report")
    lines.append(blank())
    lines.extend(_book(connection))
    lines.append(blank())
    lines.extend(_quantities(connection, bulking, deduction))
    lines.append(blank())
    lines.extend(_time(connection))
    lines.append(blank())
    lines.extend(_estimates(connection))
    return lines


def _book(connection: sqlite3.Connection) -> list[str]:
    through = measured_through(connection)
    return [
        pair("reaches", f"{len(reaches.listed(connection)):,}"),
        pair("surveys", f"{len(surveys.listed(connection)):,}"),
        pair("trips", f"{len(trips.listed(connection)):,}"),
        pair("shifts", f"{len(shifts.listed(connection)):,}"),
        pair("measured to", through.isoformat() if through else "nothing measured"),
    ]


def _quantities(connection: sqlite3.Connection, bulking: Bulking, deduction: float) -> list[str]:
    gathered = by_group(connection, bulking, deduction=deduction)
    if not gathered:
        return ["Nothing measured yet."]
    try:
        contract = contracts.only(connection)
    except Exception:  # noqa: BLE001
        contract = None
    body = []
    for group, yards in sorted(gathered.items()):
        bid = "-"
        priced = "-"
        if contract is not None:
            try:
                item = contract.for_group(group)
                bid = f"{item.estimated:,.0f}"
                priced = str(Money(round(item.unit_price.cents * yards.yards)))
            except Exception:  # noqa: BLE001
                bid = "no item"
        body.append((group, yards.rounded(), bid, priced))
    lines = table(("pay group", "measured", "bid", "earned"), body, GROUP_WIDTHS)
    lines.append(blank())
    lines.append(pair("total", total(gathered.values()).rounded()))
    missing = unmeasured(connection, bulking)
    if missing:
        lines.append(blank())
        lines.append(f"{len(missing)} reaches not measured yet")
        lines.extend(indent(f"{ident}  {reason}" for ident, reason in missing))
    return lines


def _time(connection: sqlite3.Connection) -> list[str]:
    worked = shifts.listed(connection)
    if not worked:
        return ["No shift logged."]
    got = tally(worked)
    return [
        pair("gross", f"{got.gross_hours:,.2f} hours"),
        pair("effective", f"{got.effective_hours:,.2f} hours ({got.share_effective:.1%})"),
        pair("allowable", f"{got.allowable_hours:,.2f} hours"),
        pair("standby", f"{got.standby_hours:,.2f} hours"),
        pair("contractor", f"{got.contractor_hours:,.2f} hours"),
        pair("days earned", f"{extension(worked):,}"),
    ]


def _estimates(connection: sqlite3.Connection) -> list[str]:
    try:
        contract = contracts.only(connection)
    except Exception:  # noqa: BLE001
        return ["No contract in this book."]
    written = estimates.listed(connection, contract.number)
    if not written:
        return ["No estimate written yet."]
    body = [(one.ident, one.through.isoformat(), str(one.earned), str(one.due)) for one in written]
    lines = table(("estimate", "through", "earned to date", "due"), body, ESTIMATE_WIDTHS)
    lines.append(blank())
    lines.append(pair("retained", str(written[-1].retained)))
    lines.append(pair("paid", str(written[-1].payable)))
    return lines
