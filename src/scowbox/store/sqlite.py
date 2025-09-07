"""Connections, and closing them.

A sqlite connection is a context manager for its *transaction*. Leaving a
``with connect(...)`` block commits and leaves the connection open, which is
exactly the shape of a leak that nothing complains about until Python 3.13
raises ResourceWarning on collection and the suite fails somewhere unrelated.

So the only way this package gets a connection is ``opened()``, which closes.
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from scowbox.errors import FieldError, StateError

PRAGMAS = (
    "PRAGMA foreign_keys = ON",
    "PRAGMA journal_mode = TRUNCATE",
    "PRAGMA synchronous = FULL",
)


PLAIN_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def sql_identifier(name: str) -> str:
    """A table or column name to splice into a statement.

    Sqlite will not take an identifier as a parameter, so a statement naming a
    table worked out at runtime has to be built by hand. This is the only place
    that is allowed to happen, and it happens behind a pattern that admits
    nothing but a plain name.
    """
    if not PLAIN_NAME.match(name):
        raise FieldError("identifier", f"{name!r} is not a plain sqlite identifier")
    return name


def sql_integer(value: object) -> str:
    """A whole number to splice into a pragma, which takes no parameters either."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise FieldError("integer", f"{value!r} is not a whole number")
    return str(value)


def configure(connection: sqlite3.Connection) -> sqlite3.Connection:
    """Set the pragmas and the row factory every connection in the book uses."""
    connection.row_factory = sqlite3.Row
    for pragma in PRAGMAS:
        connection.execute(pragma)
    return connection


@contextmanager
def opened(path: str | Path) -> Iterator[sqlite3.Connection]:
    """Open the book, configure it, and close it whatever happens."""
    connection = sqlite3.connect(str(path), isolation_level=None)
    try:
        yield configure(connection)
    finally:
        connection.close()


@contextmanager
def written(connection: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Run a group of writes as one transaction, rolling back on any error."""
    connection.execute("BEGIN IMMEDIATE")
    try:
        yield connection
    except BaseException:
        connection.execute("ROLLBACK")
        raise
    connection.execute("COMMIT")


def one(connection: sqlite3.Connection, sql: str, args: tuple[object, ...] = ()) -> sqlite3.Row:
    """Fetch exactly one row, or say which query expected one and got none."""
    cursor = connection.execute(sql, args)
    try:
        row: sqlite3.Row | None = cursor.fetchone()
    finally:
        cursor.close()
    if row is None:
        raise StateError(f"expected a row from {sql.split()[0].lower()} and found none")
    return row


def rows(
    connection: sqlite3.Connection, sql: str, args: tuple[object, ...] = ()
) -> list[sqlite3.Row]:
    """Fetch every row of a query and close the cursor behind it."""
    cursor = connection.execute(sql, args)
    try:
        found: list[sqlite3.Row] = cursor.fetchall()
    finally:
        cursor.close()
    return found
