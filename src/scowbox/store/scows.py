"""Scows in the book."""

from __future__ import annotations

import sqlite3

from scowbox.errors import DuplicateError, MissingError
from scowbox.model.scow import Scow
from scowbox.store.sqlite import rows, written

COLUMNS = "ident, name, inside_length, inside_width, inside_depth"


def _read(row: sqlite3.Row) -> Scow:
    return Scow(
        ident=row["ident"],
        name=row["name"],
        inside_length=row["inside_length"],
        inside_width=row["inside_width"],
        inside_depth=row["inside_depth"],
    )


def add(connection: sqlite3.Connection, scow: Scow) -> None:
    """Write a scow that is not in the book yet."""
    with written(connection):
        try:
            connection.execute(
                f"INSERT INTO scow ({COLUMNS}) VALUES (?,?,?,?,?)",
                (
                    scow.ident,
                    scow.name,
                    scow.inside_length,
                    scow.inside_width,
                    scow.inside_depth,
                ),
            )
        except sqlite3.IntegrityError:
            raise DuplicateError("scow", scow.ident) from None


def get(connection: sqlite3.Connection, ident: str) -> Scow:
    found = rows(connection, f"SELECT {COLUMNS} FROM scow WHERE ident = ?", (ident,))
    if not found:
        raise MissingError("scow", ident)
    return _read(found[0])


def listed(connection: sqlite3.Connection) -> tuple[Scow, ...]:
    """Every scow, by identifier."""
    return tuple(
        _read(row) for row in rows(connection, f"SELECT {COLUMNS} FROM scow ORDER BY ident")
    )


def remove(connection: sqlite3.Connection, ident: str) -> None:
    get(connection, ident)
    with written(connection):
        connection.execute("DELETE FROM scow WHERE ident = ?", (ident,))
