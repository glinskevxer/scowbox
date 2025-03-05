"""Reaches in the book."""

from __future__ import annotations

import sqlite3

from scowbox.errors import DuplicateError, MissingError
from scowbox.model.channel import Method, Reach, Template
from scowbox.store.sqlite import rows, written
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline, Station

COLUMNS = """
    ident, name, station_begin, station_end, bottom_width, authorized_depth,
    side_slope, advance_maintenance, overdepth, method, pay_group
"""


def _read(row: sqlite3.Row) -> Reach:
    return Reach(
        ident=row["ident"],
        name=row["name"],
        line=Reachline(Station(row["station_begin"]), Station(row["station_end"])),
        template=Template(
            bottom_width=row["bottom_width"],
            authorized_depth=Depth(row["authorized_depth"]),
            side_slope=row["side_slope"],
            advance_maintenance=row["advance_maintenance"],
            overdepth=row["overdepth"],
        ),
        method=Method(row["method"]),
        group=row["pay_group"],
    )


def add(connection: sqlite3.Connection, reach: Reach) -> None:
    """Write a reach that is not in the book yet."""
    with written(connection):
        try:
            connection.execute(
                f"INSERT INTO reach ({COLUMNS}) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    reach.ident,
                    reach.name,
                    reach.line.begin.hundredths,
                    reach.line.end.hundredths,
                    reach.template.bottom_width,
                    reach.template.authorized_depth.hundredths,
                    reach.template.side_slope,
                    reach.template.advance_maintenance,
                    reach.template.overdepth,
                    reach.method.value,
                    reach.group,
                ),
            )
        except sqlite3.IntegrityError:
            raise DuplicateError("reach", reach.ident) from None


def get(connection: sqlite3.Connection, ident: str) -> Reach:
    """One reach by identifier."""
    found = rows(connection, f"SELECT {COLUMNS} FROM reach WHERE ident = ?", (ident,))
    if not found:
        raise MissingError("reach", ident)
    return _read(found[0])


def listed(connection: sqlite3.Connection) -> tuple[Reach, ...]:
    """Every reach, in station order down the channel."""
    found = rows(connection, f"SELECT {COLUMNS} FROM reach ORDER BY station_begin")
    return tuple(_read(row) for row in found)


def in_group(connection: sqlite3.Connection, group: str) -> tuple[Reach, ...]:
    """Every reach billed under one pay item group."""
    found = rows(
        connection,
        f"SELECT {COLUMNS} FROM reach WHERE pay_group = ? ORDER BY station_begin",
        (group,),
    )
    return tuple(_read(row) for row in found)


def overlapping(connection: sqlite3.Connection, line: Reachline) -> tuple[Reach, ...]:
    """Every reach that shares any length with a run of channel."""
    found = rows(
        connection,
        f"SELECT {COLUMNS} FROM reach"
        " WHERE station_begin < ? AND station_end > ? ORDER BY station_begin",
        (line.end.hundredths, line.begin.hundredths),
    )
    return tuple(_read(row) for row in found)


def remove(connection: sqlite3.Connection, ident: str) -> None:
    """Take a reach out of the book."""
    get(connection, ident)
    with written(connection):
        connection.execute("DELETE FROM reach WHERE ident = ?", (ident,))
