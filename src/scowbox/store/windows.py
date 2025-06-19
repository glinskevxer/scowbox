"""Environmental windows in the book.

Keyed on name, reach and start date together. The same closure runs every year
under the same name, and a book that holds several seasons of a project needs
this year's loggerhead window and last year's to sit side by side.
"""

from __future__ import annotations

import datetime as dt
import sqlite3

from scowbox.errors import MissingError
from scowbox.model.window import ALL_REACHES, Restriction, Window
from scowbox.store.sqlite import rows, written
from scowbox.store.writing import inserting
from scowbox.windows.schedule import Schedule

COLUMNS = "name, reach, begins, ends, restriction, authority"


def _read(row: sqlite3.Row) -> Window:
    return Window(
        name=row["name"],
        begins=dt.date.fromisoformat(row["begins"]),
        ends=dt.date.fromisoformat(row["ends"]),
        restriction=Restriction(row["restriction"]),
        authority=row["authority"],
        reach=row["reach"],
    )


def add(connection: sqlite3.Connection, window: Window) -> None:
    """Write a window that is not in the book yet."""
    with written(connection), inserting("window", f"{window.name} {window.begins}"):
        connection.execute(
            f"INSERT INTO window_period ({COLUMNS}) VALUES (?,?,?,?,?,?)",
            (
                window.name,
                window.reach,
                window.begins.isoformat(),
                window.ends.isoformat(),
                window.restriction.value,
                window.authority,
            ),
        )


def listed(connection: sqlite3.Connection) -> tuple[Window, ...]:
    """Every window, in date order."""
    found = rows(connection, f"SELECT {COLUMNS} FROM window_period ORDER BY begins, name")
    return tuple(_read(row) for row in found)


def schedule(connection: sqlite3.Connection) -> Schedule:
    """Every window, ready to be asked what governs a day."""
    return Schedule.of(listed(connection))


def covering(connection: sqlite3.Connection, day: dt.date, reach: str) -> tuple[Window, ...]:
    """The windows in force on a reach on a day, strictest first."""
    found = rows(
        connection,
        f"SELECT {COLUMNS} FROM window_period"
        " WHERE begins <= ? AND ends >= ? AND (reach = ? OR reach = ?)"
        " ORDER BY begins, name",
        (day.isoformat(), day.isoformat(), reach, ALL_REACHES),
    )
    return Schedule.of(_read(row) for row in found).in_force(day, reach)


def remove(connection: sqlite3.Connection, name: str, reach: str, begins: dt.date) -> None:
    """Take one window out of the book."""
    found = rows(
        connection,
        f"SELECT {COLUMNS} FROM window_period WHERE name = ? AND reach = ? AND begins = ?",
        (name, reach, begins.isoformat()),
    )
    if not found:
        raise MissingError("window", f"{name} on {begins}")
    with written(connection):
        connection.execute(
            "DELETE FROM window_period WHERE name = ? AND reach = ? AND begins = ?",
            (name, reach, begins.isoformat()),
        )
