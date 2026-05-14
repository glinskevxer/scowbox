"""What stands between here and a final estimate.

The last month of a dredging contract is spent finding out what was never
finished, and every item on that list has been sitting in the book for months.
This gathers them in one pass: reaches nobody can measure, trips nobody
ticketed, surveys nobody can reduce, reaches in dispute, and whatever the
compliance sweep is still holding.

Nothing here decides anything. It reads the book and says what is outstanding,
in the order somebody would work through it.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass

from scowbox.boxmeasure.bulking import Bulking
from scowbox.compliance.findings import Severity
from scowbox.errors import MissingError, RuleError
from scowbox.job.quantities import determined, tide_for, unmeasured
from scowbox.job.sweeping import gather
from scowbox.store import contracts, estimates, reaches, surveys, trips


@dataclass(frozen=True)
class Closeout:
    """Everything outstanding on the job, in one reading."""

    unmeasured: tuple[tuple[str, str], ...]
    unticketed: tuple[str, ...]
    unreduced: tuple[tuple[str, str], ...]
    disputed: tuple[str, ...]
    violations: int
    warnings: int
    estimates: int
    closed: bool

    @property
    def outstanding(self) -> int:
        """How many things are in the way of a final estimate."""
        return (
            len(self.unmeasured)
            + len(self.unticketed)
            + len(self.unreduced)
            + len(self.disputed)
            + self.violations
        )

    @property
    def closeable(self) -> bool:
        return self.outstanding == 0 and not self.closed


def closeout(
    connection: sqlite3.Connection,
    bulking: Bulking,
    *,
    closed_through: dt.date | None = None,
) -> Closeout:
    """Read the book for everything that is not finished."""
    swept = gather(connection, closed_through)
    counted = {severity: 0 for severity in Severity}
    for finding in swept.findings:
        counted[finding.severity] += 1
    written = _estimates(connection)
    return Closeout(
        unmeasured=unmeasured(connection, bulking),
        unticketed=trips.untick(connection),
        unreduced=_unreduced(connection),
        disputed=_disputed(connection, bulking),
        violations=counted[Severity.VIOLATION],
        warnings=counted[Severity.WARNING],
        estimates=written[0],
        closed=written[1],
    )


def _unreduced(connection: sqlite3.Connection) -> tuple[tuple[str, str], ...]:
    found = []
    for survey in surveys.listed(connection):
        try:
            tide_for(connection, survey)
        except (MissingError, RuleError) as why:
            found.append((survey.ident, str(why)))
    return tuple(found)


def _disputed(connection: sqlite3.Connection, bulking: Bulking) -> tuple[str, ...]:
    found = []
    for reach in reaches.listed(connection):
        held = determined(connection, reach.ident, bulking)
        if held is not None and held.reconcile:
            found.append(reach.ident)
    return tuple(found)


def _estimates(connection: sqlite3.Connection) -> tuple[int, bool]:
    try:
        contract = contracts.only(connection)
    except MissingError:
        return 0, False
    written = estimates.listed(connection, contract.number)
    return len(written), any(one.final for one in written)
