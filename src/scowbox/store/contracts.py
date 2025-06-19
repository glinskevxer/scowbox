"""The contract and its bid schedule in the book.

A contract is written once and read constantly, so it comes back whole: the
header and every line item in one call. Nothing here supports a partial
contract, because an estimate built against half a bid schedule is an estimate
that is missing lines nobody will notice are gone.
"""

from __future__ import annotations

import datetime as dt
import sqlite3

from scowbox.errors import MissingError
from scowbox.model.contract import Contract, LineItem, Unit
from scowbox.store.sqlite import rows, written
from scowbox.store.writing import inserting
from scowbox.units.money import Money

HEADER = "number, awarded, notice_to_proceed, days, retainage, liquidated"
ITEM = "ident, contract, description, unit, unit_price, pay_group, estimated"


def _read_item(row: sqlite3.Row) -> LineItem:
    return LineItem(
        ident=row["ident"],
        description=row["description"],
        unit=Unit(row["unit"]),
        unit_price=Money(row["unit_price"]),
        group=row["pay_group"],
        estimated=row["estimated"],
    )


def add(connection: sqlite3.Connection, contract: Contract) -> None:
    """Write a contract and its whole bid schedule."""
    with written(connection):
        with inserting("contract", contract.number):
            connection.execute(
                f"INSERT INTO contract ({HEADER}) VALUES (?,?,?,?,?,?)",
                (
                    contract.number,
                    contract.awarded.isoformat(),
                    contract.notice_to_proceed.isoformat(),
                    contract.days,
                    contract.retainage,
                    contract.liquidated.cents,
                ),
            )
        for item in contract.items:
            with inserting("line item", item.ident, references="contract"):
                connection.execute(
                    f"INSERT INTO line_item ({ITEM}) VALUES (?,?,?,?,?,?,?)",
                    (
                        item.ident,
                        contract.number,
                        item.description,
                        item.unit.value,
                        item.unit_price.cents,
                        item.group,
                        item.estimated,
                    ),
                )


def get(connection: sqlite3.Connection, number: str) -> Contract:
    """A contract with every line item on it."""
    found = rows(connection, f"SELECT {HEADER} FROM contract WHERE number = ?", (number,))
    if not found:
        raise MissingError("contract", number)
    header = found[0]
    items = rows(
        connection,
        f"SELECT {ITEM} FROM line_item WHERE contract = ? ORDER BY ident",
        (number,),
    )
    return Contract(
        number=header["number"],
        awarded=dt.date.fromisoformat(header["awarded"]),
        notice_to_proceed=dt.date.fromisoformat(header["notice_to_proceed"]),
        days=header["days"],
        retainage=header["retainage"],
        liquidated=Money(header["liquidated"]),
        items=tuple(_read_item(row) for row in items),
    )


def numbers(connection: sqlite3.Connection) -> tuple[str, ...]:
    """Every contract number the book holds."""
    return tuple(
        row["number"] for row in rows(connection, "SELECT number FROM contract ORDER BY number")
    )


def only(connection: sqlite3.Connection) -> Contract:
    """The contract, where the book holds exactly one."""
    held = numbers(connection)
    if not held:
        raise MissingError("contract", "in this book")
    if len(held) > 1:
        raise MissingError("one contract", f"the book holds {len(held)}")
    return get(connection, held[0])
