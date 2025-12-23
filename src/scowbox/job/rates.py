"""Gathering production out of the book.

The average load is worked out from the trips that were actually measured, not
from the scow's box capacity. A scow rated at twenty five hundred yards that
comes in at eighteen hundred every trip is a scow that is being loaded to a
draft limit, and pricing the unmeasured trips at its capacity would invent
yards nobody dug.
"""

from __future__ import annotations

import datetime as dt
import sqlite3

from scowbox.boxmeasure.box import measure
from scowbox.measure.production import Rate, by_day, over
from scowbox.store import scows, shifts, trips
from scowbox.units.volume import Yards, total


def average_load(connection: sqlite3.Connection, reach: str | None = None) -> Yards:
    """The mean measured load, over the trips that carry a box measure."""
    fleet = {s.ident: s for s in scows.listed(connection)}
    hauled = trips.for_reach(connection, reach) if reach else trips.listed(connection)
    measured = [
        measure(fleet[trip.scow], trip).scow_yards
        for trip in hauled
        if trip.measured and trip.scow in fleet
    ]
    if not measured:
        return Yards.zero()
    return Yards(total(measured).hundredths // len(measured))


def for_reach(connection: sqlite3.Connection, reach: str, yards: Yards) -> Rate:
    """The rate over one reach, given the quantity somebody else determined."""
    worked = shifts.for_reach(connection, reach)
    hauled = trips.for_reach(connection, reach)
    return over(worked, yards, len(hauled))


def daily(
    connection: sqlite3.Connection, reach: str | None = None
) -> tuple[tuple[dt.date, Rate], ...]:
    """A rate for every day worked, priced at the average measured load."""
    worked = shifts.for_reach(connection, reach) if reach else shifts.listed(connection)
    hauled = trips.for_reach(connection, reach) if reach else trips.listed(connection)
    return by_day(worked, hauled, average_load(connection, reach))
