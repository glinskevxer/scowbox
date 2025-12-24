"""Looking backwards through a reach's surveys.

Which pair to compare is a question with an obvious wrong answer: the first and
the last. That spans the dredging as well as the shoaling, so a reach dug in
March and sounded again in September comes out scouring at forty thousand yards
a year.

The pair that means something is two consecutive surveys with no dredging
between them, and the record of what dredging happened is the shift log. So the
pairs offered here are consecutive surveys whose interval holds no shift on
that reach.
"""

from __future__ import annotations

import sqlite3
from itertools import pairwise

from scowbox.errors import MissingError
from scowbox.job.quantities import tide_for
from scowbox.measure.shoaling import MIN_SPAN_DAYS, Shoaling, shoaling
from scowbox.model.survey import Survey
from scowbox.store import reaches, shifts, surveys


def quiet_pairs(
    connection: sqlite3.Connection, reach: str, *, min_days: int = MIN_SPAN_DAYS
) -> tuple[tuple[Survey, Survey], ...]:
    """Consecutive surveys of a reach with no shift worked between them."""
    held = [s for s in surveys.for_reach(connection, reach) if s.reduces]
    worked = [s.day for s in shifts.for_reach(connection, reach)]
    found = []
    for earlier, later in pairwise(held):
        days = (later.taken_on - earlier.taken_on).days
        if days < min_days:
            continue
        if any(earlier.taken_on <= day <= later.taken_on for day in worked):
            continue
        found.append((earlier, later))
    return tuple(found)


def latest_shoaling(
    connection: sqlite3.Connection, reach: str, *, min_days: int = MIN_SPAN_DAYS
) -> Shoaling:
    """The most recent quiet interval on a reach, worked out."""
    pairs = quiet_pairs(connection, reach, min_days=min_days)
    if not pairs:
        raise MissingError("quiet interval between surveys of", reach)
    earlier, later = pairs[-1]
    return shoaling(
        reaches.get(connection, reach),
        surveys.full(connection, earlier.ident),
        surveys.full(connection, later.ident),
        tide_for(connection, earlier),
        tide_for(connection, later),
        min_days=min_days,
    )


def every_shoaling(
    connection: sqlite3.Connection, *, min_days: int = MIN_SPAN_DAYS
) -> tuple[Shoaling, ...]:
    """The most recent quiet interval on every reach that has one."""
    found = []
    for reach in reaches.listed(connection):
        try:
            found.append(latest_shoaling(connection, reach.ident, min_days=min_days))
        except MissingError:
            continue
    return tuple(found)
