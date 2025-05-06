"""The scow quantity for a reach.

Box measure every trip, add the scow yards up, divide by the bulking factor to
get back to yards of bed, then take off the share that would have been outside
the pay prism.

That last step is the awkward one. A scow does not know where the prism is. The
material in it came from wherever the bucket went, and on a scow measured reach
nothing surveyed the cut, so there is no prism to clip against. The contract
handles that with a deduction: the share of removed material that the nearest
surveyed reach found outside its own prism is applied to this one. It is an
estimate standing in for a measurement, and the report says so rather than
letting a reader think the number came off a survey.

Trips whose box measure is suspect are still counted. Leaving them out would
understate the quantity on the strength of a trim reading, and the decision to
throw a scow load out belongs to the inspector, not to the arithmetic. They
come back named so somebody makes that decision on purpose.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from scowbox.boxmeasure.box import BoxMeasure, measure
from scowbox.boxmeasure.bulking import Bulking
from scowbox.errors import FieldError, MissingError, RuleError
from scowbox.model.channel import Reach
from scowbox.model.scow import Scow, ScowTrip
from scowbox.units.volume import Yards, total


@dataclass(frozen=True)
class ScowQuantity:
    """What a stack of box measure sheets says came out of one reach."""

    reach: str
    bulking: Bulking
    deduction: float
    measures: tuple[BoxMeasure, ...]
    unmeasured: tuple[str, ...]
    suspect: tuple[str, ...]

    @property
    def trips(self) -> int:
        return len(self.measures) + len(self.unmeasured)

    @property
    def scow_yards(self) -> Yards:
        return total(m.scow_yards for m in self.measures)

    @property
    def place_yards(self) -> Yards:
        """Scow yards taken back to the room they occupied in the bed."""
        return self.bulking.in_place(self.scow_yards)

    @property
    def pay(self) -> Yards:
        """In place yards less the deduction standing in for a prism."""
        return self.place_yards.scaled(1 - self.deduction)

    @property
    def deducted(self) -> Yards:
        return self.place_yards - self.pay


def scow_quantity(
    reach: Reach,
    fleet: Mapping[str, Scow],
    trips: Iterable[ScowTrip],
    bulking: Bulking,
    *,
    deduction: float = 0.0,
) -> ScowQuantity:
    """Work a reach's trips up into a quantity."""
    if not reach.method.takes_scow:
        raise RuleError(f"{reach.ident} is measured by {reach.method.value}, not by scow")
    if not 0 <= deduction < 1:
        raise FieldError("deduction", "a deduction is a share of the quantity, under one")
    measures = []
    unmeasured = []
    suspect = []
    for trip in trips:
        if trip.reach != reach.ident:
            raise FieldError("trips", f"{trip.ident} came out of {trip.reach}")
        if not trip.measured:
            unmeasured.append(trip.ident)
            continue
        scow = fleet.get(trip.scow)
        if scow is None:
            raise MissingError("scow", trip.scow)
        got = measure(scow, trip)
        measures.append(got)
        if not got.sound:
            suspect.append(trip.ident)
    return ScowQuantity(
        reach=reach.ident,
        bulking=bulking,
        deduction=deduction,
        measures=tuple(measures),
        unmeasured=tuple(unmeasured),
        suspect=tuple(suspect),
    )
