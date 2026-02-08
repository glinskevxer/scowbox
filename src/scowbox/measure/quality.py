"""Whether a survey is good enough to pay against.

Two questions, and a survey can fail either while looking perfectly reasonable
in a plot.

Repeatability. Where a survey has sounded the same point twice, the two
readings should agree. They never agree exactly, and the size of the
disagreement is the only direct measure of the survey's own error that the
survey contains. A pair half a foot apart on a forty two foot channel is a
survey somebody should look at before it is used to bill a quantity.

Coverage. A survey can be repeatable and still have sounded a third of the
channel. The width actually covered at each section is measured against the
width the template needs, and a section that falls short is named.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from scowbox.datum.reduce import Shot
from scowbox.errors import FieldError
from scowbox.model.channel import Template
from scowbox.units.station import Station

TOLERANCE_FEET = 0.5
NEARBY_FEET = 2.0


@dataclass(frozen=True)
class Repeat:
    """Two or more readings of one point, and how far apart they were."""

    station: Station
    offset: float
    readings: int
    spread: float

    @property
    def inside(self) -> bool:
        return self.spread <= TOLERANCE_FEET


@dataclass(frozen=True)
class Quality:
    """What a survey says about itself."""

    shots: int
    stations: int
    repeats: tuple[Repeat, ...]
    short: tuple[tuple[Station, float, float], ...]

    @property
    def worst(self) -> float:
        return max((r.spread for r in self.repeats), default=0.0)

    @property
    def outside(self) -> tuple[Repeat, ...]:
        return tuple(r for r in self.repeats if not r.inside)

    @property
    def repeatable(self) -> bool:
        return not self.outside

    @property
    def covered(self) -> bool:
        return not self.short

    @property
    def sound(self) -> bool:
        return self.repeatable and self.covered


def _key(shot: Shot, nearby: float) -> tuple[int, int]:
    """A point, rounded so that two shots a foot apart are the same point."""
    return (shot.station.hundredths, round(shot.offset / nearby))


def repeats(shots: Iterable[Shot], *, nearby: float = NEARBY_FEET) -> tuple[Repeat, ...]:
    """Every point sounded more than once, worst disagreement first."""
    if nearby <= 0:
        raise FieldError("nearby", "two shots are the same point within some distance")
    gathered: dict[tuple[int, int], list[Shot]] = {}
    for shot in shots:
        gathered.setdefault(_key(shot, nearby), []).append(shot)
    found = []
    for group in gathered.values():
        if len(group) < 2:
            continue
        beds = [s.bed.feet for s in group]
        found.append(
            Repeat(
                station=group[0].station,
                offset=round(sum(s.offset for s in group) / len(group), 2),
                readings=len(group),
                spread=round(max(beds) - min(beds), 3),
            )
        )
    return tuple(sorted(found, key=lambda r: (-r.spread, r.station.hundredths, r.offset)))


def coverage(
    shots: Sequence[Shot], template: Template, *, share: float = 0.9
) -> tuple[tuple[Station, float, float], ...]:
    """Every station whose shots do not span enough of the template width."""
    if not 0 < share <= 1:
        raise FieldError("share", "the share of a template a survey must cover is under one")
    wanted = template.bottom_width * share
    by_station: dict[Station, list[float]] = {}
    for shot in shots:
        by_station.setdefault(shot.station, []).append(shot.offset)
    found = []
    for station, offsets in sorted(by_station.items(), key=lambda pair: pair[0].hundredths):
        spanned = max(offsets) - min(offsets)
        if spanned < wanted:
            found.append((station, round(spanned, 2), round(wanted, 2)))
    return tuple(found)


def quality(
    shots: Sequence[Shot],
    template: Template,
    *,
    nearby: float = NEARBY_FEET,
    share: float = 0.9,
) -> Quality:
    """Read a reduced survey back for repeatability and coverage."""
    return Quality(
        shots=len(shots),
        stations=len({s.station for s in shots}),
        repeats=repeats(shots, nearby=nearby),
        short=coverage(shots, template, share=share),
    )
