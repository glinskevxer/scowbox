"""What it would take for the two measurements to agree.

A reach outside the tolerance is an argument, and the argument is always about
the same three numbers: the tolerance itself, the bulking factor and the
deduction. Any one of them can be moved to make the two answers meet, and
knowing which one would have to move how far is most of the conversation.

None of these is a recommendation. A bulking factor of 1.61 is outside the
range any soil comes in, and reporting it as the factor that would settle the
reach is a way of saying the disagreement is not about bulking at all.
"""

from __future__ import annotations

from dataclasses import dataclass

from scowbox.boxmeasure.bulking import MAX_FACTOR, MIN_FACTOR, Bulking
from scowbox.errors import RuleError
from scowbox.measure.governing import Determination, spread_between
from scowbox.units.volume import Yards


@dataclass(frozen=True)
class Sensitivity:
    """What would have to move, and how far, for a reach to agree with itself."""

    reach: str
    survey: Yards
    scow: Yards
    bulking: Bulking

    @property
    def spread(self) -> float:
        """The tolerance that would just admit this pair."""
        return spread_between(self.survey, self.scow)

    @property
    def factor(self) -> float | None:
        """The bulking factor at which the scows would match the survey.

        Scow yards divided by the factor is the in place quantity, so the
        factor that matches a survey is the one that scales the current answer
        by the ratio between them.
        """
        if self.survey.hundredths <= 0 or self.scow.hundredths <= 0:
            return None
        return round(self.bulking.factor * self.scow.hundredths / self.survey.hundredths, 3)

    @property
    def credible(self) -> bool:
        """True when that factor is one a soil could actually have."""
        wanted = self.factor
        return wanted is not None and MIN_FACTOR <= wanted <= MAX_FACTOR

    @property
    def deduction(self) -> float | None:
        """The deduction that would bring the scow quantity down to the survey.

        Nothing where the scows are already the lesser of the two: a deduction
        only ever takes a quantity away, so it cannot close a gap the other way.
        """
        if self.scow.hundredths <= 0 or self.survey.hundredths > self.scow.hundredths:
            return None
        return round(1 - self.survey.hundredths / self.scow.hundredths, 4)

    @property
    def difference(self) -> Yards:
        return self.survey - self.scow

    def describe(self) -> str:
        return (
            f"{self.reach}: survey {self.survey.rounded()},"
            f" scow {self.scow.rounded()}, {self.spread:.1%} apart"
        )


def sensitivity(found: Determination, bulking: Bulking) -> Sensitivity:
    """Work out what would have to move on a reach measured both ways."""
    if found.survey is None or found.scow is None:
        raise RuleError(f"{found.reach} was not measured both ways, so nothing has to move")
    return Sensitivity(reach=found.reach, survey=found.survey, scow=found.scow, bulking=bulking)
