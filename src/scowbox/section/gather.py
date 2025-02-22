"""Getting shots onto sections.

A survey vessel runs lines down the channel and shoots continuously. Almost
nothing lands exactly on a section station. The standard treatment is a
corridor: every shot within half a corridor width of a section is projected
onto it, and everything else is left out of the computation entirely.

Two things here are worth stating out loud. A shot equidistant from two
sections goes to the one behind it, not the one ahead, so that the assignment
does not depend on which section the loop happened to visit first. And shots
that fall in no corridor are counted and handed back rather than dropped
quietly: a survey that put two thirds of its shots between the sections is a
survey run to the wrong interval, and the quantity computed from the remaining
third will look perfectly reasonable.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from scowbox.datum.reduce import Shot
from scowbox.errors import FieldError
from scowbox.section.bedline import Profile
from scowbox.units.station import Station

DEFAULT_CORRIDOR_FEET = 10.0
MIN_SHOTS_PER_SECTION = 2


@dataclass(frozen=True)
class Gathering:
    """What the corridors caught, and what they did not."""

    profiles: tuple[Profile, ...]
    stray: int
    thin: tuple[Station, ...]

    @property
    def caught(self) -> int:
        return sum(len(p.points) for p in self.profiles)

    @property
    def share_used(self) -> float:
        """Fraction of the shots that landed on a section, to the hundredth."""
        offered = self.caught + self.stray
        if offered == 0:
            return 0.0
        return round(self.caught / offered, 2)


def nearest_station(shot: Shot, stations: Sequence[Station], corridor: float) -> Station | None:
    """The section a shot belongs to, or nothing when it is between them."""
    half = corridor / 2
    best: Station | None = None
    best_away = half
    for station in stations:
        away = abs(shot.station - station)
        if away < best_away or (away == best_away and best is None):
            if away > half:
                continue
            best, best_away = station, away
    return best


def gather(
    shots: Iterable[Shot],
    stations: Sequence[Station],
    corridor: float = DEFAULT_CORRIDOR_FEET,
) -> Gathering:
    """Project shots onto section stations and report what was left over."""
    if corridor <= 0:
        raise FieldError("corridor", "a section corridor has a width")
    if not stations:
        raise FieldError("stations", "there are no sections to gather onto")
    ordered = sorted(stations, key=lambda s: s.hundredths)
    caught: dict[Station, list[Shot]] = {s: [] for s in ordered}
    stray = 0
    for shot in shots:
        home = nearest_station(shot, ordered, corridor)
        if home is None:
            stray += 1
            continue
        caught[home].append(Shot(home, shot.offset, shot.bed))
    profiles = []
    thin = []
    for station in ordered:
        here = caught[station]
        if len({s.offset for s in here}) < MIN_SHOTS_PER_SECTION:
            thin.append(station)
            continue
        profiles.append(Profile.of_shots(station, here))
    return Gathering(tuple(profiles), stray, tuple(thin))
