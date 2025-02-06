"""The bed across one station.

A profile is the line the bed makes across the channel at one station: a run of
offsets from the centreline, each with the elevation the survey found there.
Between two shots it is a straight line, because that is the assumption average
end area is built on and mixing a different one in here would quietly change
the quantity.

Outside the shots it is nothing at all. A profile does not extend its end
points sideways to reach the toe of a slope. If the survey did not cover the
full template the section is short, and something above has to decide what to
do about that.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from scowbox.datum.reduce import Shot
from scowbox.errors import FieldError, MissingError
from scowbox.units.depth import Elevation
from scowbox.units.station import Station


@dataclass(frozen=True)
class Point:
    """One offset across the channel and the elevation found there."""

    offset: float
    bed: Elevation


@dataclass(frozen=True)
class Profile:
    """The bed line across one station, left to right."""

    station: Station
    points: tuple[Point, ...]

    def __post_init__(self) -> None:
        if len(self.points) < 2:
            raise FieldError("points", "a profile needs at least two shots to be a line")
        offsets = [p.offset for p in self.points]
        if offsets != sorted(offsets):
            raise FieldError("points", "a profile runs left to right")
        if len(set(offsets)) != len(offsets):
            raise FieldError("points", "a profile has one elevation per offset")

    @classmethod
    def of_shots(cls, station: Station, shots: Iterable[Shot]) -> Profile:
        """Build a profile from the shots on one station.

        Two shots on the same offset are averaged. That happens where survey
        lines cross, and picking one of the pair by arrival order would make
        the quantity depend on the order the file was read in.
        """
        gathered: dict[float, list[int]] = {}
        for shot in shots:
            if shot.station != station:
                continue
            gathered.setdefault(shot.offset, []).append(shot.bed.hundredths)
        points = tuple(
            Point(offset, Elevation(round(sum(heights) / len(heights))))
            for offset, heights in sorted(gathered.items())
        )
        return cls(station, points)

    @property
    def left(self) -> float:
        return self.points[0].offset

    @property
    def right(self) -> float:
        return self.points[-1].offset

    @property
    def width(self) -> float:
        return self.right - self.left

    def covers(self, offset: float) -> bool:
        return self.left <= offset <= self.right

    def at(self, offset: float) -> Elevation:
        """The bed elevation at an offset, straight line between shots."""
        if not self.covers(offset):
            raise MissingError("shot at offset", f"{offset:g}")
        low, high = _bracket(self.points, offset)
        if low is high:
            return low.bed
        share = (offset - low.offset) / (high.offset - low.offset)
        rise = high.bed.hundredths - low.bed.hundredths
        return Elevation(round(low.bed.hundredths + rise * share))

    def clipped(self, left: float, right: float) -> Profile:
        """The part of the profile between two offsets, ends interpolated."""
        if right <= left:
            raise FieldError("clip", "the right of a clip lies right of its left")
        inner_left = max(left, self.left)
        inner_right = min(right, self.right)
        if inner_right <= inner_left:
            raise MissingError("profile between offsets", f"{left:g} and {right:g}")
        kept = [p for p in self.points if inner_left < p.offset < inner_right]
        points = [Point(inner_left, self.at(inner_left))]
        points.extend(kept)
        points.append(Point(inner_right, self.at(inner_right)))
        return Profile(self.station, tuple(points))

    def offsets(self) -> tuple[float, ...]:
        return tuple(p.offset for p in self.points)


def _bracket(points: Sequence[Point], offset: float) -> tuple[Point, Point]:
    """The two points an offset falls between, or one point twice on a hit."""
    for index, point in enumerate(points):
        if point.offset == offset:
            return point, point
        if point.offset > offset:
            return points[index - 1], point
    return points[-1], points[-1]
