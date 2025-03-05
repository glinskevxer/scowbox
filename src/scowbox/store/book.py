"""Opening a project book.

One function, because there is one right way to do it: open the file, bring the
schema up to date, hand back the connection, close it on the way out. A book
that does not exist yet is only created when the caller asked for that, so a
typo in a path opens an empty project rather than silently making one.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from scowbox.errors import MissingError
from scowbox.store.migrations import migrate
from scowbox.store.sqlite import opened


@contextmanager
def book(path: str | Path, *, create: bool = False) -> Iterator[sqlite3.Connection]:
    """Open a project book, migrating it, and close it afterwards."""
    where = Path(path)
    if not create and not where.exists():
        raise MissingError("book", str(where))
    with opened(where) as connection:
        migrate(connection)
        yield connection


def counts(connection: sqlite3.Connection) -> dict[str, int]:
    """How many rows each table of the book holds, for a quick look."""
    cursor = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")
    try:
        names = [row["name"] for row in cursor.fetchall()]
    finally:
        cursor.close()
    found = {}
    for name in names:
        inner = connection.execute(f"SELECT count(*) AS n FROM {name}")
        try:
            found[name] = int(inner.fetchone()["n"])
        finally:
            inner.close()
    return found
