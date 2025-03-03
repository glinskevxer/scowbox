"""Schema versions.

Every change to the book's shape is a numbered migration that runs once and is
never edited afterwards. The version lives in ``PRAGMA user_version``, which
sqlite keeps in the file header, so a book carries its own version around
rather than needing a table to hold it.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from scowbox.errors import StateError
from scowbox.store.sqlite import written


@dataclass(frozen=True)
class Migration:
    """One numbered step in the schema's history."""

    version: int
    name: str
    statements: tuple[str, ...]


MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        1,
        "channel",
        (
            """
            CREATE TABLE reach (
                ident TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                station_begin INTEGER NOT NULL,
                station_end INTEGER NOT NULL,
                bottom_width REAL NOT NULL,
                authorized_depth INTEGER NOT NULL,
                side_slope REAL NOT NULL,
                advance_maintenance REAL NOT NULL,
                overdepth REAL NOT NULL,
                method TEXT NOT NULL,
                pay_group TEXT NOT NULL,
                CHECK (station_end > station_begin),
                CHECK (bottom_width > 0)
            )
            """,
            "CREATE INDEX reach_by_group ON reach (pay_group)",
        ),
    ),
)


def version_of(connection: sqlite3.Connection) -> int:
    """The schema version the book is at."""
    cursor = connection.execute("PRAGMA user_version")
    try:
        return int(cursor.fetchone()[0])
    finally:
        cursor.close()


def latest() -> int:
    """The version a freshly migrated book ends up at."""
    return MIGRATIONS[-1].version


def pending(connection: sqlite3.Connection) -> tuple[Migration, ...]:
    """Migrations this book has not run yet."""
    at = version_of(connection)
    if at > latest():
        raise StateError(f"book is at version {at}, past the {latest()} this program knows")
    return tuple(m for m in MIGRATIONS if m.version > at)


def migrate(connection: sqlite3.Connection) -> tuple[str, ...]:
    """Run every pending migration and report which ones ran."""
    ran = []
    for migration in pending(connection):
        with written(connection):
            for statement in migration.statements:
                connection.execute(statement)
            connection.execute(f"PRAGMA user_version = {migration.version}")
        ran.append(migration.name)
    return tuple(ran)
