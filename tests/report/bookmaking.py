"""The records the report suites build their books out of.

Six suites had written these four records out, and they had drifted: two of
them gave the reach a three to one side slope and the rest a vertical wall, so
the same report was tested against two different prisms depending on which file
you were reading.
"""

from __future__ import annotations

import datetime as dt
import sqlite3

from scowbox.model.channel import Method, Reach, Template
from scowbox.model.placement import Ground, PlacementArea
from scowbox.model.plant import Dredge, Plant
from scowbox.model.scow import BoxReading, Corner, Scow, ScowTrip
from scowbox.model.shift import Downtime, Shift
from scowbox.store import placements, reaches, scows, shifts, trips
from scowbox.units.clock import moment
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline

REACH = "RCH-012"
SCOW = "SC-004"
AREA = "PA-002"
DREDGE = "DR-003"


def a_template() -> Template:
    """A six hundred foot bottom, vertical walls, two feet of each allowance."""
    return Template(
        bottom_width=600,
        authorized_depth=Depth.of_feet(42),
        side_slope=0,
        advance_maintenance=2,
        overdepth=2,
    )


def a_reach(
    ident: str = REACH,
    *,
    method: Method = Method.SCOW,
    group: str = "base",
    line: str = "100+00",
    to: str = "103+00",
) -> Reach:
    return Reach(
        ident=ident,
        name="Lower Range",
        line=Reachline.parse(line, to),
        template=a_template(),
        method=method,
        group=group,
    )


def a_scow(ident: str = SCOW) -> Scow:
    """A hundred and eighty by forty two by fourteen, so a full box is 3,920 cy."""
    return Scow(ident, "Dixie 41", 180, 42, 14)


def an_area(ident: str = AREA) -> PlacementArea:
    return PlacementArea(ident, "Wilmington ODMDS", Ground.OCEAN, "SAW-2019-01142")


def a_dredge(ident: str = DREDGE) -> Dredge:
    return Dredge(ident, "Cherokee", Plant.MECHANICAL, "Norfolk Dredging")


def with_plant(connection: sqlite3.Connection, **over: object) -> None:
    """A book with one reach, one scow, one placement area and one dredge."""
    reaches.add(connection, a_reach(**over))  # type: ignore[arg-type]
    scows.add(connection, a_scow())
    placements.add(connection, an_area())
    shifts.add_dredge(connection, a_dredge())


def a_trip(
    connection: sqlite3.Connection,
    ident: str,
    day: dt.date,
    *,
    loaded: float | None = 4.0,
) -> None:
    """One scow load, measured unless the caller asks for it bare."""
    readings = () if loaded is None else tuple(BoxReading(c, 12.0, loaded) for c in Corner)
    trips.add(connection, ScowTrip(ident, SCOW, REACH, day, AREA, readings))


def a_shift(
    connection: sqlite3.Connection,
    ident: str,
    day: dt.date,
    *stops: Downtime,
    began: str = "06:00",
    ended: str = "18:00",
) -> None:
    """One shift, with whatever interruptions the caller hands over."""
    shifts.add(
        connection,
        Shift(ident, DREDGE, REACH, moment(day, began), moment(day, ended), stops),
    )
