"""Running the compliance sweep over everything in the book.

This started life inside the audit report, which was fine until the closeout
wanted the same reading and the layer check caught a job module importing a
report. Gathering records and handing them to the rules is work; rendering the
answer is a report. It was always the former.
"""

from __future__ import annotations

import datetime as dt
import sqlite3

from scowbox.compliance.sweep import Sweep, sweep
from scowbox.store import placements, shifts, trips, windows


def gather(connection: sqlite3.Connection, closed_through: dt.date | None = None) -> Sweep:
    """Run the sweep over everything the book holds."""
    areas = {area.ident: area for area in placements.listed(connection)}
    tickets = [ticket for area in areas for ticket in trips.tickets_for_area(connection, area)]
    return sweep(
        shifts.listed(connection),
        trips.listed(connection),
        tickets,
        areas,
        windows.schedule(connection),
        closed_through=closed_through,
    )
