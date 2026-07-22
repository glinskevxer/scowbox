"""Dredges and shift logs in the book.

Downtime rows hang off the shift and are keyed on the moment they began, which
makes a duplicated interruption a write error rather than a quantity that is
quietly two hours short.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Sequence

from scowbox.errors import MissingError
from scowbox.model.plant import Dredge, Plant
from scowbox.model.shift import Downtime, Reason, Shift
from scowbox.store.sqlite import rows, written
from scowbox.store.writing import inserting
from scowbox.units.clock import aware

DREDGE_COLUMNS = "ident, name, plant, operator"
SHIFT_COLUMNS = "ident, dredge, reach, began, ended"


def _read_dredge(row: sqlite3.Row) -> Dredge:
    return Dredge(
        ident=row["ident"],
        name=row["name"],
        plant=Plant(row["plant"]),
        operator=row["operator"],
    )


def _read_shift(row: sqlite3.Row) -> Shift:
    return Shift(
        ident=row["ident"],
        dredge=row["dredge"],
        reach=row["reach"],
        began=dt.datetime.fromisoformat(row["began"]),
        ended=dt.datetime.fromisoformat(row["ended"]),
    )


def _read_downtime(row: sqlite3.Row) -> Downtime:
    return Downtime(
        began=dt.datetime.fromisoformat(row["began"]),
        ended=dt.datetime.fromisoformat(row["ended"]),
        reason=Reason(row["reason"]),
        note=row["note"],
    )


def add_dredge(connection: sqlite3.Connection, dredge: Dredge) -> None:
    """Write a dredge that is not in the book yet."""
    with written(connection), inserting("dredge", dredge.ident):
        connection.execute(
            f"INSERT INTO dredge ({DREDGE_COLUMNS}) VALUES (?,?,?,?)",
            (dredge.ident, dredge.name, dredge.plant.value, dredge.operator),
        )


def dredge(connection: sqlite3.Connection, ident: str) -> Dredge:
    """One dredge by identifier."""
    found = rows(connection, f"SELECT {DREDGE_COLUMNS} FROM dredge WHERE ident = ?", (ident,))
    if not found:
        raise MissingError("dredge", ident)
    return _read_dredge(found[0])


def dredges(connection: sqlite3.Connection) -> tuple[Dredge, ...]:
    """Every dredge on the job, by identifier."""
    found = rows(connection, f"SELECT {DREDGE_COLUMNS} FROM dredge ORDER BY ident")
    return tuple(_read_dredge(row) for row in found)


def add(connection: sqlite3.Connection, shift: Shift) -> None:
    """Write a shift and its interruptions."""
    with written(connection):
        with inserting("shift", shift.ident, references="dredge or reach for"):
            connection.execute(
                f"INSERT INTO shift ({SHIFT_COLUMNS}) VALUES (?,?,?,?,?)",
                (
                    shift.ident,
                    shift.dredge,
                    shift.reach,
                    aware(shift.began).isoformat(),
                    aware(shift.ended).isoformat(),
                ),
            )
        _write_downtimes(connection, shift.ident, shift.downtimes)


def _write_downtimes(connection: sqlite3.Connection, ident: str, stops: Sequence[Downtime]) -> None:
    connection.executemany(
        "INSERT INTO downtime (shift, began, ended, reason, note) VALUES (?,?,?,?,?)",
        [
            (
                ident,
                aware(stop.began).isoformat(),
                aware(stop.ended).isoformat(),
                stop.reason.value,
                stop.note,
            )
            for stop in stops
        ],
    )


def stop(connection: sqlite3.Connection, ident: str, interruption: Downtime) -> None:
    """Add one interruption to a shift already in the book."""
    held = get(connection, ident)
    rebuilt = Shift(
        ident=held.ident,
        dredge=held.dredge,
        reach=held.reach,
        began=held.began,
        ended=held.ended,
        downtimes=(*held.downtimes, interruption),
    )
    with written(connection):
        connection.execute("DELETE FROM downtime WHERE shift = ?", (ident,))
        _write_downtimes(connection, ident, rebuilt.downtimes)


def get(connection: sqlite3.Connection, ident: str) -> Shift:
    """A shift with its interruptions, oldest first."""
    found = rows(connection, f"SELECT {SHIFT_COLUMNS} FROM shift WHERE ident = ?", (ident,))
    if not found:
        raise MissingError("shift", ident)
    shift = _read_shift(found[0])
    stops = rows(
        connection,
        "SELECT began, ended, reason, note FROM downtime WHERE shift = ? ORDER BY began",
        (ident,),
    )
    if not stops:
        return shift
    return _with_stops(shift, tuple(_read_downtime(row) for row in stops))


def _with_stops(shift: Shift, stops: tuple[Downtime, ...]) -> Shift:
    """A copy of a shift carrying its interruptions."""
    return Shift(
        ident=shift.ident,
        dredge=shift.dredge,
        reach=shift.reach,
        began=shift.began,
        ended=shift.ended,
        downtimes=stops,
    )


def _gather(connection: sqlite3.Connection, found: list[sqlite3.Row]) -> tuple[Shift, ...]:
    """Build a run of shifts, fetching every interruption in one query."""
    stops: dict[str, list[Downtime]] = {}
    for row in rows(
        connection,
        "SELECT shift, began, ended, reason, note FROM downtime ORDER BY shift, began",
    ):
        stops.setdefault(row["shift"], []).append(_read_downtime(row))
    built = []
    for row in found:
        shift = _read_shift(row)
        mine = stops.get(shift.ident)
        built.append(shift if not mine else _with_stops(shift, tuple(mine)))
    return tuple(built)


def between(connection: sqlite3.Connection, first: dt.date, last: dt.date) -> tuple[Shift, ...]:
    """Every shift begun in a period, both ends included."""
    return _gather(
        connection,
        rows(
            connection,
            f"SELECT {SHIFT_COLUMNS} FROM shift WHERE began >= ? AND began < ? ORDER BY began",
            (first.isoformat(), (last + dt.timedelta(days=1)).isoformat()),
        ),
    )


def listed(connection: sqlite3.Connection) -> tuple[Shift, ...]:
    """Every shift in the book, oldest first."""
    return _gather(
        connection, rows(connection, f"SELECT {SHIFT_COLUMNS} FROM shift ORDER BY began")
    )


def for_reach(connection: sqlite3.Connection, reach: str) -> tuple[Shift, ...]:
    """Every shift worked on one reach, oldest first."""
    return _gather(
        connection,
        rows(
            connection,
            f"SELECT {SHIFT_COLUMNS} FROM shift WHERE reach = ? ORDER BY began",
            (reach,),
        ),
    )
