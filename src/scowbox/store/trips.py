"""Scow trips, their box readings and their placement tickets.

A trip is written when the scow is filled and the ticket is written when it is
emptied, which can be the following morning. So the two are separate rows and a
trip with no ticket is a normal state of affairs, not a broken record. What is
not normal is a ticket for a load the box measure never measured, and the
reports are built to notice that rather than the store to forbid it.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Sequence

from scowbox.errors import MissingError
from scowbox.model.placement import Grade, PlacementTicket
from scowbox.model.scow import BoxReading, Corner, ScowTrip
from scowbox.store.sqlite import rows, written
from scowbox.store.writing import inserting
from scowbox.units.clock import aware
from scowbox.units.volume import Yards

COLUMNS = "ident, scow, reach, loaded_on, placement"
TICKET_COLUMNS = "trip, area, released, yards, grade"


def _read_trip(row: sqlite3.Row) -> ScowTrip:
    return ScowTrip(
        ident=row["ident"],
        scow=row["scow"],
        reach=row["reach"],
        loaded_on=dt.date.fromisoformat(row["loaded_on"]),
        placement=row["placement"],
    )


def _read_ticket(row: sqlite3.Row) -> PlacementTicket:
    return PlacementTicket(
        trip=row["trip"],
        area=row["area"],
        released=dt.datetime.fromisoformat(row["released"]),
        yards=Yards(row["yards"]),
        grade=Grade(row["grade"]),
    )


def add(connection: sqlite3.Connection, trip: ScowTrip) -> None:
    """Write a trip, and its box readings if it is carrying any."""
    with written(connection):
        with inserting("trip", trip.ident, references="scow, reach or placement area for"):
            connection.execute(
                f"INSERT INTO trip ({COLUMNS}) VALUES (?,?,?,?,?)",
                (
                    trip.ident,
                    trip.scow,
                    trip.reach,
                    trip.loaded_on.isoformat(),
                    trip.placement,
                ),
            )
        _write_readings(connection, trip.ident, trip.readings)


def _write_readings(
    connection: sqlite3.Connection, ident: str, readings: Sequence[BoxReading]
) -> None:
    connection.executemany(
        "INSERT INTO box_reading (trip, corner, light, loaded) VALUES (?,?,?,?)",
        [(ident, r.corner.value, r.light, r.loaded) for r in readings],
    )


def measure(connection: sqlite3.Connection, ident: str, readings: Sequence[BoxReading]) -> None:
    """Replace a trip's box readings."""
    get(connection, ident)
    with written(connection):
        connection.execute("DELETE FROM box_reading WHERE trip = ?", (ident,))
        _write_readings(connection, ident, readings)


def get(connection: sqlite3.Connection, ident: str) -> ScowTrip:
    """A trip with whatever box readings it holds."""
    found = rows(connection, f"SELECT {COLUMNS} FROM trip WHERE ident = ?", (ident,))
    if not found:
        raise MissingError("trip", ident)
    trip = _read_trip(found[0])
    readings = rows(
        connection,
        "SELECT corner, light, loaded FROM box_reading WHERE trip = ? ORDER BY corner",
        (ident,),
    )
    if not readings:
        return trip
    return trip.with_readings(
        tuple(BoxReading(Corner(r["corner"]), r["light"], r["loaded"]) for r in readings)
    )


def _gather(connection: sqlite3.Connection, found: list[sqlite3.Row]) -> tuple[ScowTrip, ...]:
    """Build a run of trips, fetching every box reading in one query.

    This called ``get`` once a trip before, which was two queries a trip and
    four hundred queries on a season report. Sqlite is quick, and four hundred
    round trips inside a loop that is itself inside a loop is not.
    """
    readings: dict[str, list[BoxReading]] = {}
    for row in rows(
        connection,
        "SELECT trip, corner, light, loaded FROM box_reading ORDER BY trip, corner",
    ):
        readings.setdefault(row["trip"], []).append(
            BoxReading(Corner(row["corner"]), row["light"], row["loaded"])
        )
    built = []
    for row in found:
        trip = _read_trip(row)
        mine = readings.get(trip.ident)
        built.append(trip if not mine else trip.with_readings(tuple(mine)))
    return tuple(built)


def for_reach(connection: sqlite3.Connection, reach: str) -> tuple[ScowTrip, ...]:
    """Every trip out of one reach, oldest first."""
    return _gather(
        connection,
        rows(
            connection,
            f"SELECT {COLUMNS} FROM trip WHERE reach = ? ORDER BY loaded_on, ident",
            (reach,),
        ),
    )


def listed(connection: sqlite3.Connection) -> tuple[ScowTrip, ...]:
    """Every trip in the book, oldest first."""
    return _gather(
        connection, rows(connection, f"SELECT {COLUMNS} FROM trip ORDER BY loaded_on, ident")
    )


def between(connection: sqlite3.Connection, first: dt.date, last: dt.date) -> tuple[ScowTrip, ...]:
    """Every trip loaded in a period, both ends included."""
    return _gather(
        connection,
        rows(
            connection,
            f"SELECT {COLUMNS} FROM trip WHERE loaded_on BETWEEN ? AND ? ORDER BY loaded_on, ident",
            (first.isoformat(), last.isoformat()),
        ),
    )


def release(connection: sqlite3.Connection, ticket: PlacementTicket) -> None:
    """Write the ticket that closes a trip out."""
    get(connection, ticket.trip)
    with (
        written(connection),
        inserting("ticket for trip", ticket.trip, references="placement area"),
    ):
        connection.execute(
            f"INSERT INTO ticket ({TICKET_COLUMNS}) VALUES (?,?,?,?,?)",
            (
                ticket.trip,
                ticket.area,
                aware(ticket.released).isoformat(),
                ticket.yards.hundredths,
                ticket.grade.value,
            ),
        )


def ticket_of(connection: sqlite3.Connection, trip: str) -> PlacementTicket:
    """The ticket that closed a trip out."""
    found = rows(connection, f"SELECT {TICKET_COLUMNS} FROM ticket WHERE trip = ?", (trip,))
    if not found:
        raise MissingError("ticket for trip", trip)
    return _read_ticket(found[0])


def tickets_for_area(connection: sqlite3.Connection, area: str) -> tuple[PlacementTicket, ...]:
    """Every ticket released at one area, oldest first."""
    found = rows(
        connection,
        f"SELECT {TICKET_COLUMNS} FROM ticket WHERE area = ? ORDER BY released",
        (area,),
    )
    return tuple(_read_ticket(row) for row in found)


def untick(connection: sqlite3.Connection) -> tuple[str, ...]:
    """Trips that have no ticket yet, oldest first."""
    found = rows(
        connection,
        "SELECT trip.ident AS ident FROM trip"
        " LEFT JOIN ticket ON ticket.trip = trip.ident"
        " WHERE ticket.trip IS NULL ORDER BY trip.loaded_on, trip.ident",
    )
    return tuple(row["ident"] for row in found)
