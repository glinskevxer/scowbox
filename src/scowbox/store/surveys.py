"""Surveys and their soundings.

A survey's header and its shots are written separately because they arrive
separately: the header is typed in when the boat is booked and the shots come
off an export hours later. Loading shots twice would double a quantity, so
loading replaces rather than appends, and it says how many it replaced.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Sequence

from scowbox.errors import MissingError
from scowbox.model.survey import Sounding, Survey, SurveyKind
from scowbox.store.sqlite import rows, written
from scowbox.store.writing import inserting
from scowbox.units.clock import aware
from scowbox.units.depth import Depth
from scowbox.units.station import Station

HEADER = "ident, reach, kind, taken_on, vessel, transducer_draft, gauge"


def _read_header(row: sqlite3.Row) -> Survey:
    return Survey(
        ident=row["ident"],
        reach=row["reach"],
        kind=SurveyKind(row["kind"]),
        taken_on=dt.date.fromisoformat(row["taken_on"]),
        vessel=row["vessel"],
        transducer_draft=row["transducer_draft"],
        gauge=row["gauge"],
    )


def _read_sounding(row: sqlite3.Row) -> Sounding:
    return Sounding(
        station=Station(row["station"]),
        offset=row["offset_ft"],
        raw_depth=Depth(row["raw_depth"]),
        taken=dt.datetime.fromisoformat(row["taken"]),
    )


def add(connection: sqlite3.Connection, survey: Survey) -> None:
    """Write a survey header, and its shots if it is carrying any."""
    with written(connection):
        with inserting("survey", survey.ident, references="reach"):
            connection.execute(
                f"INSERT INTO survey ({HEADER}) VALUES (?,?,?,?,?,?,?)",
                (
                    survey.ident,
                    survey.reach,
                    survey.kind.value,
                    survey.taken_on.isoformat(),
                    survey.vessel,
                    survey.transducer_draft,
                    survey.gauge,
                ),
            )
        _write_soundings(connection, survey.ident, survey.soundings)


def load(
    connection: sqlite3.Connection, ident: str, soundings: Sequence[Sounding]
) -> tuple[int, int]:
    """Replace a survey's shots. Returns how many went out and how many in."""
    get(connection, ident)
    with written(connection):
        cursor = connection.execute("DELETE FROM sounding WHERE survey = ?", (ident,))
        gone = cursor.rowcount
        cursor.close()
        _write_soundings(connection, ident, soundings)
    return gone, len(soundings)


def _write_soundings(
    connection: sqlite3.Connection, ident: str, soundings: Sequence[Sounding]
) -> None:
    connection.executemany(
        "INSERT INTO sounding (survey, station, offset_ft, raw_depth, taken) VALUES (?,?,?,?,?)",
        [
            (
                ident,
                shot.station.hundredths,
                shot.offset,
                shot.raw_depth.hundredths,
                aware(shot.taken).isoformat(),
            )
            for shot in soundings
        ],
    )


def get(connection: sqlite3.Connection, ident: str) -> Survey:
    """A survey header without its shots."""
    found = rows(connection, f"SELECT {HEADER} FROM survey WHERE ident = ?", (ident,))
    if not found:
        raise MissingError("survey", ident)
    return _read_header(found[0])


def full(connection: sqlite3.Connection, ident: str) -> Survey:
    """A survey with every shot it holds, in station and offset order."""
    header = get(connection, ident)
    found = rows(
        connection,
        "SELECT station, offset_ft, raw_depth, taken FROM sounding"
        " WHERE survey = ? ORDER BY station, offset_ft",
        (ident,),
    )
    return header.with_soundings(tuple(_read_sounding(row) for row in found))


def for_reach(connection: sqlite3.Connection, reach: str) -> tuple[Survey, ...]:
    """Every survey of one reach, oldest first."""
    found = rows(
        connection,
        f"SELECT {HEADER} FROM survey WHERE reach = ? ORDER BY taken_on, ident",
        (reach,),
    )
    return tuple(_read_header(row) for row in found)


def listed(connection: sqlite3.Connection) -> tuple[Survey, ...]:
    """Every survey in the book, oldest first."""
    found = rows(connection, f"SELECT {HEADER} FROM survey ORDER BY taken_on, ident")
    return tuple(_read_header(row) for row in found)


def remove(connection: sqlite3.Connection, ident: str) -> None:
    """Take a survey and its shots out of the book."""
    get(connection, ident)
    with written(connection):
        connection.execute("DELETE FROM sounding WHERE survey = ?", (ident,))
        connection.execute("DELETE FROM survey WHERE ident = ?", (ident,))
