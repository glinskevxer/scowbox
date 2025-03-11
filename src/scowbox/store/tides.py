"""Gauge readings in the book.

A gauge publishes every six minutes, so a week of one gauge is around seventeen
hundred rows and a project holds several gauges over several months. Readings
are therefore fetched for a window rather than in full, and the window is
widened by one publication interval at each end so that a sounding taken a
minute after the last reading inside the window still has a reading ahead of it
to interpolate towards.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Sequence

from scowbox.datum.tide import TideReading, TideRecord
from scowbox.errors import MissingError
from scowbox.store.sqlite import rows, written
from scowbox.units.clock import aware

MARGIN = dt.timedelta(minutes=6)


def add_readings(
    connection: sqlite3.Connection, gauge: str, readings: Sequence[TideReading]
) -> int:
    """Write readings for a gauge, ignoring ones already held."""
    with written(connection):
        cursor = connection.executemany(
            "INSERT OR IGNORE INTO tide_reading (gauge, at, height) VALUES (?,?,?)",
            [(gauge, aware(r.at).isoformat(), r.height) for r in readings],
        )
        written_count = cursor.rowcount
        cursor.close()
    return written_count


def record_for(
    connection: sqlite3.Connection, gauge: str, begin: dt.datetime, end: dt.datetime
) -> TideRecord:
    """The gauge's readings over a window, with a margin at each end."""
    found = rows(
        connection,
        "SELECT at, height FROM tide_reading WHERE gauge = ? AND at >= ? AND at <= ? ORDER BY at",
        (gauge, (aware(begin) - MARGIN).isoformat(), (aware(end) + MARGIN).isoformat()),
    )
    if not found:
        raise MissingError("tide readings for gauge", gauge)
    return TideRecord(
        gauge,
        tuple(TideReading(dt.datetime.fromisoformat(r["at"]), r["height"]) for r in found),
    )


def gauges(connection: sqlite3.Connection) -> tuple[str, ...]:
    """Every gauge the book holds readings for."""
    found = rows(connection, "SELECT DISTINCT gauge FROM tide_reading ORDER BY gauge")
    return tuple(row["gauge"] for row in found)


def span(connection: sqlite3.Connection, gauge: str) -> tuple[dt.datetime, dt.datetime]:
    """First and last reading held for a gauge."""
    found = rows(
        connection,
        "SELECT min(at) AS first, max(at) AS last FROM tide_reading WHERE gauge = ?",
        (gauge,),
    )
    if not found or found[0]["first"] is None:
        raise MissingError("tide readings for gauge", gauge)
    return (
        dt.datetime.fromisoformat(found[0]["first"]),
        dt.datetime.fromisoformat(found[0]["last"]),
    )
