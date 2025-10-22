"""Looking after the book.

Three things a project engineer needs to be able to do without a database
administrator: check the file is sound, take a copy of it, and get the space
back after a season of edits. Sqlite does all three; this puts them where the
rest of the program can reach them and makes the copy safe to take while the
book is open.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from scowbox.errors import StateError
from scowbox.store.migrations import latest, version_of
from scowbox.store.sqlite import opened, rows


@dataclass(frozen=True)
class Health:
    """What the book says about itself."""

    version: int
    integrity: str
    orphans: tuple[str, ...]
    tables: int
    pages: int
    page_size: int

    @property
    def sound(self) -> bool:
        return self.integrity == "ok" and not self.orphans and self.version == latest()

    @property
    def bytes_used(self) -> int:
        return self.pages * self.page_size


def health(connection: sqlite3.Connection) -> Health:
    """Ask sqlite and the schema whether anything is wrong."""
    integrity = rows(connection, "PRAGMA integrity_check")[0][0]
    orphans = tuple(
        f"{row[0]} row {row[1]} points at nothing in {row[2]}"
        for row in rows(connection, "PRAGMA foreign_key_check")
    )
    tables = rows(connection, "SELECT count(*) AS n FROM sqlite_master WHERE type = 'table'")[0][
        "n"
    ]
    return Health(
        version=version_of(connection),
        integrity=str(integrity),
        orphans=orphans,
        tables=int(tables),
        pages=int(rows(connection, "PRAGMA page_count")[0][0]),
        page_size=int(rows(connection, "PRAGMA page_size")[0][0]),
    )


def backup(connection: sqlite3.Connection, where: str | Path) -> Path:
    """Copy the book to another file, safely, while it is open."""
    target = Path(where)
    if target.exists():
        raise StateError(f"{target} is already there; a backup does not overwrite")
    target.parent.mkdir(parents=True, exist_ok=True)
    with opened(target) as copy:
        connection.backup(copy)
    return target


def compact(connection: sqlite3.Connection) -> int:
    """Vacuum the book and report how many bytes it gave back.

    The figure can come back negative, and that is not a bug. Vacuuming an
    almost empty book rebuilds it from scratch and the rebuilt file needs a
    page the fragmented one had not allocated yet. A season's book gives back
    a great deal; a book with four rows in it costs one page.
    """
    before = health(connection).bytes_used
    connection.execute("VACUUM")
    return before - health(connection).bytes_used
