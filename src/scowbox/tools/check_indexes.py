"""Check: every foreign key has an index behind it.

Sqlite indexes a primary key and nothing else. A foreign key with no index on
the child side turns every delete of a parent row into a scan of the child
table, and every join through it into the same. On a book with four rows that
is invisible; on a season with sixty thousand soundings it is the difference
between a report that prints and one somebody kills.

The check reads the live schema rather than the migrations, so an index added
in one migration and dropped in a later one counts as gone.
"""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

from scowbox.store.book import book
from scowbox.store.sqlite import rows, sql_identifier
from scowbox.tools.scan import report

NAME = "check_indexes"


def tables(connection: sqlite3.Connection) -> list[str]:
    """Every table in the book, by name."""
    found = rows(
        connection,
        "SELECT name FROM sqlite_master WHERE type = 'table'"
        " AND name NOT LIKE 'sqlite_%' ORDER BY name",
    )
    return [row["name"] for row in found]


def foreign_keys(connection: sqlite3.Connection, table: str) -> list[str]:
    """The column of each foreign key on a table."""
    found = rows(connection, f"PRAGMA foreign_key_list({sql_identifier(table)})")
    return [row["from"] for row in found]


def indexed(connection: sqlite3.Connection, table: str) -> set[str]:
    """Every column that leads an index or a primary key on a table."""
    leading = set()
    for row in rows(connection, f"PRAGMA index_list({sql_identifier(table)})"):
        columns = rows(connection, f"PRAGMA index_info({sql_identifier(row['name'])})")
        if columns:
            leading.add(columns[0]["name"])
    for row in rows(connection, f"PRAGMA table_info({sql_identifier(table)})"):
        if row["pk"] == 1:
            leading.add(row["name"])
    return leading


def findings(connection: sqlite3.Connection | None = None) -> list[str]:
    """Every foreign key with nothing behind it."""
    if connection is not None:
        return _sweep(connection)
    with (
        tempfile.TemporaryDirectory() as where,
        book(Path(where) / "indexes.sqlite3", create=True) as fresh,
    ):
        return _sweep(fresh)


def _sweep(connection: sqlite3.Connection) -> list[str]:
    out: list[str] = []
    for table in tables(connection):
        have = indexed(connection, table)
        out.extend(
            f"{table}.{column} is a foreign key with no index behind it"
            for column in foreign_keys(connection, table)
            if column not in have
        )
    return out


def main() -> int:
    """Run the check and return the exit status."""
    return report(NAME, findings())


if __name__ == "__main__":
    sys.exit(main())
