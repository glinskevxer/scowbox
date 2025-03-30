"""The survey quantity, end to end.

Reduce both surveys to datum, gather their shots onto the reach's sections,
pair the sections that both surveys reached, take an end area at each pair and
average end area between them.

A station only one of the two surveys reached is not a section. It is tempting
to carry the missing side forward from the neighbouring station and keep going,
and that is how a reach the after survey never covered ends up billed at its
before areas. Unpaired stations are counted, named and left out.
"""

from __future__ import annotations

from dataclasses import dataclass

from scowbox.datum.reduce import reduce_survey
from scowbox.datum.tide import TideRecord
from scowbox.errors import FieldError, RuleError
from scowbox.model.channel import Reach
from scowbox.model.survey import Survey, SurveyKind
from scowbox.section.area import SectionArea, section_area
from scowbox.section.bedline import Profile
from scowbox.section.gather import DEFAULT_CORRIDOR_FEET, gather
from scowbox.section.prism import Cut, Prism
from scowbox.section.volume import ReachVolume, reach_volume
from scowbox.units.station import Station

DEFAULT_INTERVAL_FEET = 100.0


@dataclass(frozen=True)
class SurveyQuantity:
    """What a pair of surveys measured over one reach."""

    reach: str
    before: str
    after: str
    volume: ReachVolume
    areas: tuple[SectionArea, ...]
    unpaired: tuple[Station, ...]
    stray_before: int
    stray_after: int

    @property
    def sections(self) -> int:
        return len(self.areas)

    @property
    def paired_share(self) -> float:
        """Fraction of the reach's sections both surveys reached."""
        offered = self.sections + len(self.unpaired)
        if offered == 0:
            return 0.0
        return round(self.sections / offered, 2)


def _profiles(
    survey: Survey,
    tide: TideRecord,
    stations: list[Station],
    corridor: float,
    squat: float,
    index: float,
) -> tuple[dict[Station, Profile], int]:
    shots = reduce_survey(survey, tide, squat=squat, index=index)
    caught = gather(shots, stations, corridor)
    return {p.station: p for p in caught.profiles}, caught.stray


def survey_quantity(
    reach: Reach,
    before: Survey,
    after: Survey,
    before_tide: TideRecord,
    after_tide: TideRecord,
    *,
    interval: float = DEFAULT_INTERVAL_FEET,
    corridor: float = DEFAULT_CORRIDOR_FEET,
    squat: float = 0.0,
    index: float = 0.0,
) -> SurveyQuantity:
    """Work a pair of surveys up into a quantity for one reach."""
    _check_pair(reach, before, after)
    stations = reach.line.cuts(interval)
    ahead, stray_before = _profiles(before, before_tide, stations, corridor, squat, index)
    behind, stray_after = _profiles(after, after_tide, stations, corridor, squat, index)
    prism = Prism.of_template(reach.template, Cut.PAY)
    areas = []
    unpaired = []
    for station in stations:
        first, second = ahead.get(station), behind.get(station)
        if first is None or second is None:
            unpaired.append(station)
            continue
        areas.append(section_area(first, second, prism))
    if len(areas) < 2:
        raise RuleError(f"{reach.ident} has {len(areas)} paired sections, which is not a volume")
    return SurveyQuantity(
        reach=reach.ident,
        before=before.ident,
        after=after.ident,
        volume=reach_volume(reach.ident, areas),
        areas=tuple(areas),
        unpaired=tuple(unpaired),
        stray_before=stray_before,
        stray_after=stray_after,
    )


def _check_pair(reach: Reach, before: Survey, after: Survey) -> None:
    if before.reach != reach.ident:
        raise FieldError("before", f"{before.ident} is a survey of {before.reach}")
    if after.reach != reach.ident:
        raise FieldError("after", f"{after.ident} is a survey of {after.reach}")
    if before.kind is not SurveyKind.BEFORE:
        raise RuleError(f"{before.ident} is a {before.kind.value} survey, not a before")
    if after.kind is not SurveyKind.AFTER:
        raise RuleError(f"{after.ident} is a {after.kind.value} survey, not an after")
    if after.taken_on < before.taken_on:
        raise RuleError(
            f"{after.ident} was run on {after.taken_on}, before {before.ident} on {before.taken_on}"
        )
    if not reach.method.takes_survey:
        raise RuleError(f"{reach.ident} is measured by {reach.method.value}, not by survey")
