"""The standing rules, written where a reader can find them.

Every one of these is enforced somewhere in the package and tested somewhere in
the suite. They are gathered here because somebody arriving at a quantity they
did not expect needs the list, and reading it out of thirty modules is not a
thing anybody does twice.

Nothing imports this to make a decision. It is a description of decisions taken
elsewhere, and `scowbox.tools.check_design` is the reason it cannot quietly
stop being true: the module names in each law have to resolve.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Law:
    """One standing rule, and where it is enforced."""

    subject: str
    rule: str
    where: str

    def line(self) -> str:
        return f"{self.subject:<14}{self.rule}"


LAWS: tuple[Law, ...] = (
    Law(
        "depths",
        "a depth is positive downward and an elevation positive upward",
        "scowbox.units.depth",
    ),
    Law(
        "money",
        "amounts are whole cents and an extension rounds once",
        "scowbox.units.money",
    ),
    Law(
        "volumes",
        "volumes are hundredths of a cubic yard, and feet become yards in one place",
        "scowbox.units.volume",
    ),
    Law(
        "prism",
        "the overdepth carries down the side slopes, it is not a shelf",
        "scowbox.section.prism",
    ),
    Law(
        "sections",
        "average end area, and never over more than two hundred feet",
        "scowbox.section.volume",
    ),
    Law(
        "tide",
        "no reduction against an extrapolated tide, and none across a wide gap",
        "scowbox.datum.tide",
    ),
    Law(
        "box measure",
        "four corners, every time, and a light reading inside the box",
        "scowbox.boxmeasure.box",
    ),
    Law(
        "governing",
        "inside the tolerance the survey governs, outside it the lesser does",
        "scowbox.measure.governing",
    ),
    Law(
        "reconciling",
        "a signed reconciliation beats both measurements and is never re-derived",
        "scowbox.model.reconciliation",
    ),
    Law(
        "unmeasured",
        "a reach nobody measured is left out, not billed at nothing",
        "scowbox.job.quantities",
    ),
    Law(
        "estimates",
        "every line is cumulative, and retainage comes off the earned amount",
        "scowbox.pay.estimate",
    ),
    Law(
        "final",
        "the final estimate needs everything measured and every trip ticketed",
        "scowbox.job.estimating",
    ),
    Law(
        "downtime",
        "allowable time buys days, standby time buys money, and most buys neither",
        "scowbox.pay.timeloss",
    ),
    Law(
        "windows",
        "the strictest window in force governs, whatever order they were written",
        "scowbox.windows.schedule",
    ),
    Law(
        "placement",
        "grade first, then capacity, so a violation never reads as a near miss",
        "scowbox.measure.placing",
    ),
    Law(
        "the clock",
        "nothing asks the machine what day it is",
        "scowbox.tools.check_clock",
    ),
)


def subjects() -> tuple[str, ...]:
    """Every subject the laws are grouped under."""
    return tuple(law.subject for law in LAWS)
