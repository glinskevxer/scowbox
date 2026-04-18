"""The estimate sheet, and the history behind it.

An estimate on its own is a column of figures. Laid against the one before it,
it is a month's work, and that is the reading somebody actually wants: what
moved, on which line, and by how much.

The history is the same idea over the whole job. A line that jumps in one month
and does not move again is a line somebody caught up on; a line that moves a
little every month is the one being worked.
"""

from __future__ import annotations

import sqlite3

from scowbox.errors import MissingError
from scowbox.pay.estimate import Estimate
from scowbox.report.lines import blank, heading, pair, table
from scowbox.store import contracts, estimates

LINE_WIDTHS = (10, 26, 13, 13, 13)
HISTORY_WIDTHS = (10, 12, 16, 16, 16)


def render(connection: sqlite3.Connection, ident: str) -> list[str]:
    """One estimate, laid against the one before it."""
    one = estimates.get(connection, ident)
    before = _previous(connection, one)
    lines = heading(f"Estimate {one.number}  {one.ident}")
    lines.append(blank())
    lines.append(pair("contract", one.contract))
    lines.append(pair("through", one.through.isoformat()))
    lines.append(pair("previous", before.ident if before else "none"))
    lines.append(pair("final", "yes" if one.final else "no"))
    lines.append(blank())
    lines.extend(_lines(one))
    lines.append(blank())
    lines.extend(_money(one))
    return lines


def _previous(connection: sqlite3.Connection, one: Estimate) -> Estimate | None:
    for other in estimates.listed(connection, one.contract):
        if other.number == one.number - 1:
            return other
    return None


def _lines(one: Estimate) -> list[str]:
    body = [
        (
            line.item,
            line.description[:25],
            f"{line.previous:,.2f}",
            f"{line.to_date:,.2f}",
            str(line.earned_this_period),
        )
        for line in one.lines
    ]
    return table(("item", "description", "previous", "to date", "this period"), body, LINE_WIDTHS)


def _money(one: Estimate) -> list[str]:
    lines = [
        pair("earned", str(one.earned)),
        pair("retained", str(-one.retained)),
    ]
    if one.final:
        lines.append(pair("released", str(one.released)))
    if one.days_late:
        lines.append(pair("damages", f"{-one.liquidated} over {one.days_late} days"))
    lines.append(pair("payable", str(one.payable)))
    lines.append(pair("paid before", str(-one.paid_before)))
    lines.append(pair("due", str(one.due)))
    return lines


def history(connection: sqlite3.Connection, number: str | None = None) -> list[str]:
    """Every estimate on the contract, first to last."""
    held = contracts.get(connection, number) if number else contracts.only(connection)
    written = estimates.listed(connection, held.number)
    lines = heading(f"Estimates, {held.number}")
    lines.append(blank())
    if not written:
        lines.append("No estimate written yet.")
        return lines
    body = [
        (
            one.ident,
            one.through.isoformat(),
            str(one.earned),
            str(one.retained),
            str(one.due),
        )
        for one in written
    ]
    lines.extend(table(("estimate", "through", "earned", "retained", "due"), body, HISTORY_WIDTHS))
    lines.append(blank())
    lines.append(pair("paid to date", str(written[-1].payable)))
    lines.append(pair("still held", str(written[-1].retained)))
    return lines


def item_history(connection: sqlite3.Connection, item: str, number: str | None = None) -> list[str]:
    """One line item across every estimate it appears on."""
    held = contracts.get(connection, number) if number else contracts.only(connection)
    lines = heading(f"Line item {item}")
    lines.append(blank())
    body = []
    for one in estimates.listed(connection, held.number):
        try:
            line = one.line(item)
        except MissingError:
            continue
        body.append(
            (
                one.ident,
                one.through.isoformat(),
                f"{line.previous:,.2f}",
                f"{line.to_date:,.2f}",
                str(line.earned_this_period),
            )
        )
    if not body:
        lines.append(f"{item} is on no estimate in this book.")
        return lines
    lines.extend(
        table(
            ("estimate", "through", "previous", "to date", "this period"),
            body,
            LINE_WIDTHS,
        )
    )
    return lines
