"""Contract modifications in the book."""

from __future__ import annotations

import datetime as dt
import sqlite3

from scowbox.errors import MissingError
from scowbox.model.modification import Change, Modification
from scowbox.store.sqlite import rows, written
from scowbox.store.writing import inserting
from scowbox.units.money import Money

COLUMNS = "number, contract, signed_on, change, description, days, item, price"


def _read(row: sqlite3.Row) -> Modification:
    held = row["price"]
    return Modification(
        number=row["number"],
        signed_on=dt.date.fromisoformat(row["signed_on"]),
        change=Change(row["change"]),
        description=row["description"],
        days=row["days"],
        item=row["item"],
        price=None if held is None else Money(held),
    )


def add(connection: sqlite3.Connection, contract: str, modification: Modification) -> None:
    """Write a modification against a contract in the book."""
    with written(connection), inserting("modification", modification.number, references="contract"):
        connection.execute(
            f"INSERT INTO modification ({COLUMNS}) VALUES (?,?,?,?,?,?,?,?)",
            (
                modification.number,
                contract,
                modification.signed_on.isoformat(),
                modification.change.value,
                modification.description,
                modification.days,
                modification.item,
                None if modification.price is None else modification.price.cents,
            ),
        )


def get(connection: sqlite3.Connection, contract: str, number: str) -> Modification:
    """One modification by its number."""
    found = rows(
        connection,
        f"SELECT {COLUMNS} FROM modification WHERE contract = ? AND number = ?",
        (contract, number),
    )
    if not found:
        raise MissingError("modification", number)
    return _read(found[0])


def listed(connection: sqlite3.Connection, contract: str) -> tuple[Modification, ...]:
    """Every modification on a contract, oldest first."""
    found = rows(
        connection,
        f"SELECT {COLUMNS} FROM modification WHERE contract = ? ORDER BY signed_on, number",
        (contract,),
    )
    return tuple(_read(row) for row in found)


def remove(connection: sqlite3.Connection, contract: str, number: str) -> None:
    """Take a modification back out, which is rare and deliberate."""
    get(connection, contract, number)
    with written(connection):
        connection.execute(
            "DELETE FROM modification WHERE contract = ? AND number = ?", (contract, number)
        )
