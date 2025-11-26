"""Reconciliations in the book.

One per reach, keyed on the reach, because a reach that has been settled twice
has not been settled. Replacing one is a deliberate act with its own function,
so that the ordinary write cannot quietly overwrite a signed agreement.
"""

from __future__ import annotations

import datetime as dt
import sqlite3

from scowbox.errors import MissingError
from scowbox.model.reconciliation import Accepted, Reconciliation
from scowbox.store.sqlite import rows, written
from scowbox.store.writing import inserting
from scowbox.units.volume import Yards

COLUMNS = "reach, decided_on, accepted, decided_by, note, quantity"


def _read(row: sqlite3.Row) -> Reconciliation:
    held = row["quantity"]
    return Reconciliation(
        reach=row["reach"],
        decided_on=dt.date.fromisoformat(row["decided_on"]),
        accepted=Accepted(row["accepted"]),
        decided_by=row["decided_by"],
        note=row["note"],
        quantity=None if held is None else Yards(held),
    )


def add(connection: sqlite3.Connection, settled: Reconciliation) -> None:
    """Write a reconciliation for a reach that has not been settled yet."""
    with written(connection), inserting("reconciliation for", settled.reach, references="reach"):
        connection.execute(
            f"INSERT INTO reconciliation ({COLUMNS}) VALUES (?,?,?,?,?,?)",
            (
                settled.reach,
                settled.decided_on.isoformat(),
                settled.accepted.value,
                settled.decided_by,
                settled.note,
                None if settled.quantity is None else settled.quantity.hundredths,
            ),
        )


def replace(connection: sqlite3.Connection, settled: Reconciliation) -> None:
    """Overwrite a reconciliation, which is a decision somebody has to make."""
    get(connection, settled.reach)
    with written(connection):
        connection.execute("DELETE FROM reconciliation WHERE reach = ?", (settled.reach,))
    add(connection, settled)


def get(connection: sqlite3.Connection, reach: str) -> Reconciliation:
    """The reconciliation for a reach."""
    found = rows(connection, f"SELECT {COLUMNS} FROM reconciliation WHERE reach = ?", (reach,))
    if not found:
        raise MissingError("reconciliation for", reach)
    return _read(found[0])


def find(connection: sqlite3.Connection, reach: str) -> Reconciliation | None:
    """The reconciliation for a reach, or nothing where there is none."""
    found = rows(connection, f"SELECT {COLUMNS} FROM reconciliation WHERE reach = ?", (reach,))
    return _read(found[0]) if found else None


def listed(connection: sqlite3.Connection) -> tuple[Reconciliation, ...]:
    """Every reconciliation, oldest first."""
    found = rows(connection, f"SELECT {COLUMNS} FROM reconciliation ORDER BY decided_on, reach")
    return tuple(_read(row) for row in found)


def remove(connection: sqlite3.Connection, reach: str) -> None:
    """Take a reconciliation out of the book."""
    get(connection, reach)
    with written(connection):
        connection.execute("DELETE FROM reconciliation WHERE reach = ?", (reach,))
