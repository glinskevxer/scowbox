"""Dredges and shift logs in the book.

Downtime rows hang off the shift and are keyed on the moment they began, which
makes a duplicated interruption a write error rather than a quantity that is
quietly two hours short.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Sequence

from scowbox.errors import DuplicateError, MissingError
from scowbox.model.plant import Dredge, Plant
from scowbox.model.shift import Downtime, Reason, Shift
from scowbox.store.sqlite import rows, written
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
    with written(connection):
        try:
            connection.execute(
                f"INSERT INTO dredge ({DREDGE_COLUMNS}) VALUES (?,?,?,?)",
                (dredge.ident, dredge.name, dredge.plant.value, dredge.operator),
            )
        except sqlite3.IntegrityError:
            raise DuplicateError("dredge", dredge.ident) from None


def dredge(connection: sqlite3.Connection, ident: str) -> Dredge:
    found = rows(connection, f"SELECT {DREDGE_COLUMNS} FROM dredge WHERE ident = ?", (ident,))
    if not found:
        raise MissingError("dredge", ident)
    return _read_dredge(found[0])


def dredges(connection: sqlite3.Connection) -> tuple[Dredge, ...]:
    found = rows(connection, f"SELECT {DREDGE_COLUMNS} FROM dredge ORDER BY ident")
    return tuple(_read_dredge(row) for row in found)


def add(connection: sqlite3.Connection, shift: Shift) -> None:
    """Write a shift and its interruptions."""
    with written(connection):
        try:
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
        except sqlite3.IntegrityError as error:
            if "FOREIGN KEY" in str(error):
                raise MissingError("dredge or reach for", shift.ident) from None
            raise DuplicateError("shift", shift.ident) from None
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
    return Shift(
        ident=shift.ident,
        dredge=shift.dredge,
        reach=shift.reach,
        began=shift.began,
        ended=shift.ended,
        downtimes=tuple(_read_downtime(row) for row in stops),
    )


def between(connection: sqlite3.Connection, first: dt.date, last: dt.date) -> tuple[Shift, ...]:
    """Every shift begun in a period, both ends included."""
    found = rows(
        connection,
        f"SELECT {SHIFT_COLUMNS} FROM shift WHERE began >= ? AND began < ? ORDER BY began",
        (first.isoformat(), (last + dt.timedelta(days=1)).isoformat()),
    )
    return tuple(get(connection, row["ident"]) for row in found)


def for_reach(connection: sqlite3.Connection, reach: str) -> tuple[Shift, ...]:
    found = rows(
        connection,
        f"SELECT {SHIFT_COLUMNS} FROM shift WHERE reach = ? ORDER BY began",
        (reach,),
    )
    return tuple(get(connection, row["ident"]) for row in found)
