"""Building the next estimate out of the book.

The estimate is built from whatever the book can measure on the day it is
built. That is deliberate. A reach whose after survey has not been run yet
contributes nothing this month and contributes its whole quantity next month,
and the cumulative arithmetic carries the difference. Holding an estimate back
until every reach is measured is how a contractor goes two months unpaid on
work that was finished in the first week.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass

from scowbox.boxmeasure.bulking import Bulking
from scowbox.errors import RuleError
from scowbox.job.contract import current
from scowbox.job.quantities import by_group, unmeasured
from scowbox.measure.governing import TOLERANCE
from scowbox.pay.estimate import Estimate, build
from scowbox.pay.timeloss import extension
from scowbox.store import estimates, shifts


@dataclass(frozen=True)
class Draft:
    """An estimate that has not been written to the book yet."""

    estimate: Estimate
    left_out: tuple[tuple[str, str], ...]
    days_earned: int

    @property
    def complete(self) -> bool:
        return not self.left_out


def days_late(connection: sqlite3.Connection, through: dt.date) -> tuple[int, int]:
    """How many days past completion, and how many were earned back.

    Against the modified contract time. A time extension signed in June is not
    an argument to be had again every month.
    """
    contract = current(connection)
    earned = extension(shifts.listed(connection))
    return contract.days_late(through, extension=earned), earned


def draft(
    connection: sqlite3.Connection,
    through: dt.date,
    bulking: Bulking,
    *,
    deduction: float = 0.0,
    tolerance: float = TOLERANCE,
    lump_sums: dict[str, float] | None = None,
) -> Draft:
    """Build the next estimate without writing it."""
    contract = current(connection)
    previous = estimates.latest(connection, contract.number)
    if previous is not None and through <= previous.through:
        raise RuleError(f"estimate {previous.number} already runs through {previous.through}")
    late, earned = days_late(connection, through)
    return Draft(
        estimate=build(
            contract,
            estimates.next_number(connection, contract.number),
            through,
            by_group(connection, bulking, deduction=deduction, tolerance=tolerance),
            lump_sums or {},
            previous,
            days_late=late,
        ),
        left_out=unmeasured(connection, bulking),
        days_earned=earned,
    )


def write(connection: sqlite3.Connection, drafted: Draft) -> Estimate:
    """Put a drafted estimate in the book."""
    estimates.add(connection, drafted.estimate)
    return drafted.estimate
