"""Placement areas in the book.

A capacity is held as hundredths of a cubic yard and a site without one holds
null rather than zero. Zero would be a full cell, and a cell that is full is a
different thing from an ocean site that never fills.
"""

from __future__ import annotations

import sqlite3

from scowbox.errors import DuplicateError, MissingError
from scowbox.model.placement import Ground, PlacementArea
from scowbox.store.sqlite import rows, written
from scowbox.units.volume import Yards

COLUMNS = "ident, name, ground, permit, capacity"


def _read(row: sqlite3.Row) -> PlacementArea:
    held = row["capacity"]
    return PlacementArea(
        ident=row["ident"],
        name=row["name"],
        ground=Ground(row["ground"]),
        permit=row["permit"],
        capacity=None if held is None else Yards(held),
    )


def add(connection: sqlite3.Connection, area: PlacementArea) -> None:
    """Write a placement area that is not in the book yet."""
    with written(connection):
        try:
            connection.execute(
                f"INSERT INTO placement_area ({COLUMNS}) VALUES (?,?,?,?,?)",
                (
                    area.ident,
                    area.name,
                    area.ground.value,
                    area.permit,
                    None if area.capacity is None else area.capacity.hundredths,
                ),
            )
        except sqlite3.IntegrityError:
            raise DuplicateError("placement area", area.ident) from None


def get(connection: sqlite3.Connection, ident: str) -> PlacementArea:
    found = rows(connection, f"SELECT {COLUMNS} FROM placement_area WHERE ident = ?", (ident,))
    if not found:
        raise MissingError("placement area", ident)
    return _read(found[0])


def listed(connection: sqlite3.Connection) -> tuple[PlacementArea, ...]:
    """Every placement area, by identifier."""
    found = rows(connection, f"SELECT {COLUMNS} FROM placement_area ORDER BY ident")
    return tuple(_read(row) for row in found)


def of_ground(connection: sqlite3.Connection, ground: Ground) -> tuple[PlacementArea, ...]:
    """Every area of one kind of ground."""
    found = rows(
        connection,
        f"SELECT {COLUMNS} FROM placement_area WHERE ground = ? ORDER BY ident",
        (ground.value,),
    )
    return tuple(_read(row) for row in found)


def remove(connection: sqlite3.Connection, ident: str) -> None:
    get(connection, ident)
    with written(connection):
        connection.execute("DELETE FROM placement_area WHERE ident = ?", (ident,))
