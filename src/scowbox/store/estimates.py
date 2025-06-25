"""Progress estimates in the book.

An estimate is written once and never edited. A figure that turns out to be
wrong is corrected in the next estimate, because the cumulative arithmetic
carries the correction through on its own and because the estimate that went to
the owner is the estimate that went to the owner.

So there is no update here. There is a write, a read, and a way to find the
last one, which is what the next one needs.
"""

from __future__ import annotations

import datetime as dt
import sqlite3

from scowbox.errors import MissingError
from scowbox.model.contract import Unit
from scowbox.pay.estimate import Estimate, EstimateLine
from scowbox.store.sqlite import rows, written
from scowbox.store.writing import inserting
from scowbox.units.money import Money

HEADER = "ident, contract, number, through, retainage, days_late, liquidated_rate, paid_before"
LINE = "estimate, item, description, unit, unit_price, to_date, previous"


def _read_line(row: sqlite3.Row) -> EstimateLine:
    return EstimateLine(
        item=row["item"],
        description=row["description"],
        unit=Unit(row["unit"]),
        unit_price=Money(row["unit_price"]),
        to_date=row["to_date"],
        previous=row["previous"],
    )


def add(connection: sqlite3.Connection, estimate: Estimate) -> None:
    """Write an estimate and every line on it."""
    with written(connection):
        with inserting("estimate", estimate.ident, references="contract"):
            connection.execute(
                f"INSERT INTO estimate ({HEADER}) VALUES (?,?,?,?,?,?,?,?)",
                (
                    estimate.ident,
                    estimate.contract,
                    estimate.number,
                    estimate.through.isoformat(),
                    estimate.retainage,
                    estimate.days_late,
                    estimate.liquidated_rate.cents,
                    estimate.paid_before.cents,
                ),
            )
        connection.executemany(
            f"INSERT INTO estimate_line ({LINE}) VALUES (?,?,?,?,?,?,?)",
            [
                (
                    estimate.ident,
                    line.item,
                    line.description,
                    line.unit.value,
                    line.unit_price.cents,
                    line.to_date,
                    line.previous,
                )
                for line in estimate.lines
            ],
        )


def get(connection: sqlite3.Connection, ident: str) -> Estimate:
    """One estimate with its lines, in item order."""
    found = rows(connection, f"SELECT {HEADER} FROM estimate WHERE ident = ?", (ident,))
    if not found:
        raise MissingError("estimate", ident)
    header = found[0]
    lines = rows(
        connection,
        f"SELECT {LINE} FROM estimate_line WHERE estimate = ? ORDER BY item",
        (ident,),
    )
    return Estimate(
        ident=header["ident"],
        contract=header["contract"],
        number=header["number"],
        through=dt.date.fromisoformat(header["through"]),
        retainage=header["retainage"],
        lines=tuple(_read_line(row) for row in lines),
        days_late=header["days_late"],
        liquidated_rate=Money(header["liquidated_rate"]),
        paid_before=Money(header["paid_before"]),
    )


def listed(connection: sqlite3.Connection, contract: str) -> tuple[Estimate, ...]:
    """Every estimate on a contract, first to last."""
    found = rows(
        connection,
        "SELECT ident FROM estimate WHERE contract = ? ORDER BY number",
        (contract,),
    )
    return tuple(get(connection, row["ident"]) for row in found)


def latest(connection: sqlite3.Connection, contract: str) -> Estimate | None:
    """The last estimate written on a contract, or nothing on a new job."""
    found = rows(
        connection,
        "SELECT ident FROM estimate WHERE contract = ? ORDER BY number DESC LIMIT 1",
        (contract,),
    )
    if not found:
        return None
    return get(connection, found[0]["ident"])


def next_number(connection: sqlite3.Connection, contract: str) -> int:
    """The number the next estimate on this contract takes."""
    last = latest(connection, contract)
    return 1 if last is None else last.number + 1
