"""Shoaling: how fast a reach fills back in.

The same two surveys and the same sections as a pay quantity, paired the other
way round. Where the pay computation asks how much the bed dropped, this asks
how much it rose, and the answer is what tells a district whether a channel
needs dredging every eighteen months or every five years.

It is deliberately not clipped to the pay prism. Material that shoals in above
the prism is still material in the way of a ship, and a shoaling rate that only
counted what would be paid for would understate the problem exactly where the
channel is worst.

Two surveys a fortnight apart do not give a rate. The bed moves with a storm
and settles afterwards, and dividing a fortnight's noise by a fortnight
produces a number with three significant figures and no meaning. The floor is
stated here and the caller has to pass a shorter one on purpose.
"""

from __future__ import annotations

from dataclasses import dataclass

from scowbox.datum.tide import TideRecord
from scowbox.errors import FieldError, RuleError
from scowbox.measure.fromsurvey import profiles_of
from scowbox.model.channel import Reach
from scowbox.model.survey import Survey
from scowbox.section.area import section_area
from scowbox.section.gather import DEFAULT_CORRIDOR_FEET
from scowbox.section.prism import Cut, Prism
from scowbox.section.volume import reach_volume
from scowbox.units.station import Station
from scowbox.units.volume import Yards

MIN_SPAN_DAYS = 30
DAYS_A_YEAR = 365.25


@dataclass(frozen=True)
class Shoaling:
    """What a reach gained between two surveys, and how fast."""

    reach: str
    earlier: str
    later: str
    days: int
    gained: Yards
    sections: int
    unpaired: tuple[Station, ...]

    @property
    def yards_a_day(self) -> float:
        return round(self.gained.yards / self.days, 2)

    @property
    def yards_a_year(self) -> float:
        return round(self.yards_a_day * DAYS_A_YEAR, 1)

    @property
    def filling(self) -> bool:
        """True when the bed rose. A reach can scour instead, and some do."""
        return self.gained.hundredths > 0


def shoaling(
    reach: Reach,
    earlier: Survey,
    later: Survey,
    earlier_tide: TideRecord,
    later_tide: TideRecord,
    *,
    interval: float = 100.0,
    corridor: float = DEFAULT_CORRIDOR_FEET,
    min_days: int = MIN_SPAN_DAYS,
) -> Shoaling:
    """Work out what a reach gained between two soundings of it."""
    for name, survey in (("earlier", earlier), ("later", later)):
        if survey.reach != reach.ident:
            raise FieldError(name, f"{survey.ident} is a survey of {survey.reach}")
    days = (later.taken_on - earlier.taken_on).days
    if days <= 0:
        raise RuleError(f"{later.ident} was not run after {earlier.ident}")
    if days < min_days:
        raise RuleError(
            f"{earlier.ident} and {later.ident} are {days} days apart,"
            f" under the {min_days} a rate is taken over"
        )
    stations = reach.line.cuts(interval)
    first, _ = profiles_of(earlier, earlier_tide, stations, corridor=corridor)
    second, _ = profiles_of(later, later_tide, stations, corridor=corridor)
    prism = Prism.of_template(reach.template, Cut.PAY)
    areas = []
    unpaired = []
    for station in stations:
        one, other = first.get(station), second.get(station)
        if one is None or other is None:
            unpaired.append(station)
            continue
        areas.append(section_area(other, one, prism))
    if len(areas) < 2:
        raise RuleError(f"{reach.ident} has {len(areas)} paired sections, which is not a volume")
    volume = reach_volume(reach.ident, areas)
    return Shoaling(
        reach=reach.ident,
        earlier=earlier.ident,
        later=later.ident,
        days=days,
        gained=volume.removed,
        sections=len(areas),
        unpaired=tuple(unpaired),
    )
