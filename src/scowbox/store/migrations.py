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
    Migration(
        2,
        "surveys",
        (
            """
            CREATE TABLE survey (
                ident TEXT PRIMARY KEY,
                reach TEXT NOT NULL REFERENCES reach (ident),
                kind TEXT NOT NULL,
                taken_on TEXT NOT NULL,
                vessel TEXT NOT NULL,
                transducer_draft REAL NOT NULL,
                CHECK (transducer_draft > 0)
            )
            """,
            """
            CREATE TABLE sounding (
                survey TEXT NOT NULL REFERENCES survey (ident) ON DELETE CASCADE,
                station INTEGER NOT NULL,
                offset_ft REAL NOT NULL,
                raw_depth INTEGER NOT NULL,
                taken TEXT NOT NULL,
                CHECK (raw_depth > 0)
            )
            """,
            "CREATE INDEX survey_by_reach ON survey (reach, taken_on)",
            "CREATE INDEX sounding_by_survey ON sounding (survey, station)",
        ),
    ),
    Migration(
        3,
        "tides",
        (
            """
            CREATE TABLE tide_reading (
                gauge TEXT NOT NULL,
                at TEXT NOT NULL,
                height REAL NOT NULL,
                PRIMARY KEY (gauge, at)
            )
            """,
        ),
    ),
    Migration(
        4,
        "survey gauge",
        ("ALTER TABLE survey ADD COLUMN gauge TEXT NOT NULL DEFAULT ''",),
    ),
    Migration(
        5,
        "plant and placement",
        (
            """
            CREATE TABLE scow (
                ident TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                inside_length REAL NOT NULL,
                inside_width REAL NOT NULL,
                inside_depth REAL NOT NULL,
                CHECK (inside_length > 0 AND inside_width > 0 AND inside_depth > 0)
            )
            """,
            """
            CREATE TABLE placement_area (
                ident TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                ground TEXT NOT NULL,
                permit TEXT NOT NULL,
                capacity INTEGER
            )
            """,
            "CREATE INDEX placement_by_ground ON placement_area (ground)",
        ),
    ),
    Migration(
        6,
        "trips",
        (
            """
            CREATE TABLE trip (
                ident TEXT PRIMARY KEY,
                scow TEXT NOT NULL REFERENCES scow (ident),
                reach TEXT NOT NULL REFERENCES reach (ident),
                loaded_on TEXT NOT NULL,
                placement TEXT NOT NULL REFERENCES placement_area (ident)
            )
            """,
            """
            CREATE TABLE box_reading (
                trip TEXT NOT NULL REFERENCES trip (ident) ON DELETE CASCADE,
                corner TEXT NOT NULL,
                light REAL NOT NULL,
                loaded REAL NOT NULL,
                PRIMARY KEY (trip, corner)
            )
            """,
            """
            CREATE TABLE ticket (
                trip TEXT PRIMARY KEY REFERENCES trip (ident) ON DELETE CASCADE,
                area TEXT NOT NULL REFERENCES placement_area (ident),
                released TEXT NOT NULL,
                yards INTEGER NOT NULL,
                grade TEXT NOT NULL,
                CHECK (yards > 0)
            )
            """,
            "CREATE INDEX trip_by_reach ON trip (reach, loaded_on)",
            "CREATE INDEX ticket_by_area ON ticket (area, released)",
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
