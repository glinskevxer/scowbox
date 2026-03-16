"""Working a reach's quantity out of the book.

Which surveys pair is decided here and it is decided one way: the last before
survey and the last after survey the book holds for the reach. A reach dredged
twice in a season needs two contracts' worth of records or two reaches, not a
program that guesses which of four surveys the engineer meant.

The tide comes from the gauge the survey names, over the day it was run. A
survey with no gauge named cannot be reduced and says so rather than reducing
against a flat sea.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Mapping

from scowbox.boxmeasure.bulking import Bulking
from scowbox.datum.tide import TideRecord
from scowbox.errors import MissingError, RuleError
from scowbox.measure.fromscow import ScowQuantity, scow_quantity
from scowbox.measure.fromsurvey import (
    DEFAULT_INTERVAL_FEET,
    SurveyQuantity,
    survey_quantity,
)
from scowbox.measure.governing import TOLERANCE, Determination, determine
from scowbox.model.channel import Reach
from scowbox.model.survey import Survey, SurveyKind
from scowbox.section.gather import DEFAULT_CORRIDOR_FEET
from scowbox.store import reaches, reconciliations, scows, surveys, tides, trips
from scowbox.units.clock import moment
from scowbox.units.volume import Yards

DAY_BEGINS = "00:00"
DAY_ENDS = "23:59"


def last_survey(connection: sqlite3.Connection, reach: str, kind: SurveyKind) -> Survey:
    """The most recent survey of one kind over a reach, with its shots."""
    found = [s for s in surveys.for_reach(connection, reach) if s.kind is kind]
    if not found:
        raise MissingError(f"{kind.value} survey of", reach)
    return surveys.full(connection, found[-1].ident)


def tide_for(connection: sqlite3.Connection, survey: Survey) -> TideRecord:
    """The gauge record covering the day a survey was run."""
    if not survey.reduces:
        raise RuleError(f"{survey.ident} names no gauge, so its shots cannot be reduced")
    return tides.record_for(
        connection,
        survey.gauge,
        moment(survey.taken_on, DAY_BEGINS),
        moment(survey.taken_on, DAY_ENDS),
    )


def survey_side(
    connection: sqlite3.Connection,
    reach: Reach,
    *,
    interval: float = DEFAULT_INTERVAL_FEET,
    corridor: float = DEFAULT_CORRIDOR_FEET,
    squat: float = 0.0,
    index: float = 0.0,
) -> SurveyQuantity:
    """Work the survey pair for a reach up into a quantity."""
    before = last_survey(connection, reach.ident, SurveyKind.BEFORE)
    after = last_survey(connection, reach.ident, SurveyKind.AFTER)
    return survey_quantity(
        reach,
        before,
        after,
        tide_for(connection, before),
        tide_for(connection, after),
        interval=interval,
        corridor=corridor,
        squat=squat,
        index=index,
    )


def scow_side(
    connection: sqlite3.Connection,
    reach: Reach,
    bulking: Bulking,
    *,
    deduction: float = 0.0,
) -> ScowQuantity:
    """Work the trips out of a reach up into a quantity.

    No trips at all is not a quantity of nothing. A scow measured reach nobody
    has worked yet has not been measured, and billing it at zero reads on the
    estimate exactly like a reach that was worked and came to nothing.
    """
    fleet = {scow.ident: scow for scow in scows.listed(connection)}
    hauled = trips.for_reach(connection, reach.ident)
    if not hauled:
        raise MissingError("scow trip out of", reach.ident)
    return scow_quantity(reach, fleet, hauled, bulking, deduction=deduction)


def determine_reach(
    connection: sqlite3.Connection,
    ident: str,
    bulking: Bulking,
    *,
    deduction: float = 0.0,
    tolerance: float = TOLERANCE,
    interval: float = DEFAULT_INTERVAL_FEET,
    corridor: float = DEFAULT_CORRIDOR_FEET,
) -> Determination:
    """The pay quantity for one reach, measured every way its method allows.

    A reconciliation in the book is picked up here rather than passed in. It is
    a property of the reach, not of the caller, and a report that showed the
    unsettled figure because it forgot to look would be worse than one that
    could not show it at all.
    """
    reach = reaches.get(connection, ident)
    from_survey = (
        survey_side(connection, reach, interval=interval, corridor=corridor)
        if reach.method.takes_survey
        else None
    )
    from_scow = (
        scow_side(connection, reach, bulking, deduction=deduction)
        if reach.method.takes_scow
        else None
    )
    return determine(
        reach,
        from_survey,
        from_scow,
        tolerance=tolerance,
        settled=reconciliations.find(connection, ident),
    )


def determined(
    connection: sqlite3.Connection,
    ident: str,
    bulking: Bulking,
    *,
    deduction: float = 0.0,
    tolerance: float = TOLERANCE,
) -> Determination | None:
    """The pay quantity for a reach, or nothing where it cannot be measured.

    Four callers had written this try and except round ``determine_reach`` and
    two of them caught only one of the two errors, so a reach with a survey
    pair that would not pair took a report down instead of being reported as
    unmeasured.
    """
    try:
        return determine_reach(connection, ident, bulking, deduction=deduction, tolerance=tolerance)
    except (MissingError, RuleError):
        return None


def by_group(
    connection: sqlite3.Connection,
    bulking: Bulking,
    *,
    deduction: float = 0.0,
    tolerance: float = TOLERANCE,
) -> Mapping[str, Yards]:
    """Pay quantities gathered into the groups the bid schedule bills by.

    A reach whose records are not complete enough to measure is left out rather
    than counted at nothing. Nothing and unmeasured are different, and an
    estimate that treats them alike bills the first correctly by accident.
    """
    gathered: dict[str, Yards] = {}
    for reach in reaches.listed(connection):
        found = determined(
            connection, reach.ident, bulking, deduction=deduction, tolerance=tolerance
        )
        if found is None:
            continue
        gathered[reach.group] = gathered.get(reach.group, Yards.zero()) + found.quantity
    return gathered


def unmeasured(connection: sqlite3.Connection, bulking: Bulking) -> tuple[tuple[str, str], ...]:
    """Reaches that cannot be measured yet, each with the reason."""
    missing = []
    for reach in reaches.listed(connection):
        try:
            determine_reach(connection, reach.ident, bulking)
        except (MissingError, RuleError) as trouble:
            missing.append((reach.ident, str(trouble)))
    return tuple(missing)


def measured_through(connection: sqlite3.Connection) -> dt.date | None:
    """The last day any measurement in the book was taken."""
    days = [s.taken_on for s in surveys.listed(connection)]
    days.extend(t.loaded_on for t in trips.listed(connection))
    return max(days) if days else None
