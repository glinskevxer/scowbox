"""Which measurement the contract lets you bill.

A reach measured one way has one answer and the question does not arise. A
reach measured both ways has two, and they will not agree, because they are not
measuring the same thing: the survey measures the hole and the scows measure
what came out of it, and the difference between those is every yard that
slumped back in, every yard of overflow that went over the side and every
percentage point the bulking factor is wrong by.

So the contract sets a tolerance. Inside it the survey governs, because the
survey is the direct measurement of the pay prism and the scow measure is an
inference through a bulking factor. Outside it neither is trusted, the lesser
of the two is paid on account, and the reach is flagged for reconciliation.

The lesser, not the survey. A reach where the scows say far less than the
survey did is a reach where something is wrong with the survey pair, and paying
the survey figure while that is unresolved is how an overpayment gets made that
somebody has to claw back at final.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from scowbox.errors import RuleError
from scowbox.measure.fromscow import ScowQuantity
from scowbox.measure.fromsurvey import SurveyQuantity
from scowbox.model.channel import Method, Reach
from scowbox.units.volume import Yards

TOLERANCE = 0.10
"""Share by which the two measurements may differ before a reach is flagged."""


class Governs(Enum):
    """Which measurement the quantity was taken from."""

    SURVEY = "survey"
    SCOW = "scow"
    LESSER = "lesser of the two"


@dataclass(frozen=True)
class Determination:
    """The pay quantity for one reach, and how it was arrived at."""

    reach: str
    method: Method
    survey: Yards | None
    scow: Yards | None
    quantity: Yards
    governs: Governs
    spread: float | None
    reconcile: bool
    notes: tuple[str, ...]

    @property
    def difference(self) -> Yards | None:
        """Survey less scow, where both were taken."""
        if self.survey is None or self.scow is None:
            return None
        return self.survey - self.scow


def spread_between(first: Yards, second: Yards) -> float:
    """How far apart two quantities are, as a share of the larger."""
    larger = max(first.hundredths, second.hundredths)
    if larger == 0:
        return 0.0
    return round(abs(first.hundredths - second.hundredths) / larger, 4)


def determine(
    reach: Reach,
    survey: SurveyQuantity | None = None,
    scow: ScowQuantity | None = None,
    *,
    tolerance: float = TOLERANCE,
) -> Determination:
    """Decide the pay quantity for one reach from what was measured."""
    from_survey = None if survey is None else survey.volume.pay
    from_scow = None if scow is None else scow.pay
    notes: list[str] = []
    if reach.method is Method.SURVEY:
        if from_survey is None:
            raise RuleError(f"{reach.ident} is measured by survey and has no survey quantity")
        if from_scow is not None:
            notes.append("scow measure held for the record, not billed")
        return _single(reach, from_survey, from_scow, Governs.SURVEY, from_survey, notes)
    if reach.method is Method.SCOW:
        if from_scow is None:
            raise RuleError(f"{reach.ident} is measured by scow and has no scow quantity")
        if from_survey is not None:
            notes.append("survey held for the record, not billed")
        return _single(reach, from_survey, from_scow, Governs.SCOW, from_scow, notes)
    if from_survey is None or from_scow is None:
        raise RuleError(
            f"{reach.ident} is measured both ways and is missing the"
            f" {'survey' if from_survey is None else 'scow'} quantity"
        )
    apart = spread_between(from_survey, from_scow)
    if apart <= tolerance:
        notes.append(f"agree within {apart:.1%}, survey governs")
        return Determination(
            reach=reach.ident,
            method=reach.method,
            survey=from_survey,
            scow=from_scow,
            quantity=from_survey,
            governs=Governs.SURVEY,
            spread=apart,
            reconcile=False,
            notes=tuple(notes),
        )
    notes.append(f"differ by {apart:.1%}, past the {tolerance:.0%} tolerance")
    return Determination(
        reach=reach.ident,
        method=reach.method,
        survey=from_survey,
        scow=from_scow,
        quantity=min(from_survey, from_scow),
        governs=Governs.LESSER,
        spread=apart,
        reconcile=True,
        notes=tuple(notes),
    )


def _single(
    reach: Reach,
    survey: Yards | None,
    scow: Yards | None,
    governs: Governs,
    quantity: Yards,
    notes: list[str],
) -> Determination:
    apart = None if survey is None or scow is None else spread_between(survey, scow)
    return Determination(
        reach=reach.ident,
        method=reach.method,
        survey=survey,
        scow=scow,
        quantity=quantity,
        governs=governs,
        spread=apart,
        reconcile=False,
        notes=tuple(notes),
    )
