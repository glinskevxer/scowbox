"""End areas at a station.

Two bed lines and a prism decide three areas at every station:

    removed   everything between the before line and the after line
    pay       the part of that which lies inside the pay prism
    overcut   what is left, which was still dug and is still not paid for

The integration is exact rather than sampled. All three curves are piecewise
linear, so the only places the answer bends are the shot offsets, the toes of
the prism and the points where two of the curves cross. Those crossings are
solved for and used as breakpoints, which means a section answers the same
number whether the survey put shots every ten feet or every hundred.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from itertools import pairwise

from scowbox.errors import MissingError
from scowbox.section.bedline import Profile
from scowbox.section.prism import Prism
from scowbox.units.depth import Elevation
from scowbox.units.station import Station

Curve = Callable[[float], float]

DATUM = Elevation(0)
"""Mean lower low water, the top a section is measured to unless one is given."""


@dataclass(frozen=True)
class SectionArea:
    """What one station contributes, in square feet."""

    station: Station
    removed: float
    pay: float
    left: float
    right: float

    @property
    def overcut(self) -> float:
        """Removed material that fell outside the prism."""
        return round(self.removed - self.pay, 4)


def _positive_area(x0: float, x1: float, d0: float, d1: float) -> float:
    """Integral of the positive part of a straight line between two ends."""
    if d0 >= 0 and d1 >= 0:
        return (d0 + d1) / 2 * (x1 - x0)
    if d0 <= 0 and d1 <= 0:
        return 0.0
    root = x0 + (x1 - x0) * d0 / (d0 - d1)
    if d0 > 0:
        return d0 / 2 * (root - x0)
    return d1 / 2 * (x1 - root)


def _crossing(x0: float, x1: float, a0: float, a1: float, b0: float, b1: float) -> float | None:
    """Where two straight lines cross inside an interval, if they do."""
    top = a0 - b0
    bottom = a1 - b1
    if top == 0 or bottom == 0 or (top > 0) == (bottom > 0):
        return None
    return x0 + (x1 - x0) * top / (top - bottom)


def _breaks(before: Profile, after: Profile, prism: Prism, top: Elevation) -> list[float]:
    """Every offset where one of the three curves changes direction."""
    left = max(before.left, after.left)
    right = min(before.right, after.right)
    if right <= left:
        raise MissingError("overlap between surveys", f"{before.station}")
    reach = prism.top_half_width(top)
    candidates = {left, right}
    candidates.update(o for o in before.offsets() if left < o < right)
    candidates.update(o for o in after.offsets() if left < o < right)
    for edge in (
        prism.left_toe,
        prism.right_toe,
        prism.centre - reach,
        prism.centre + reach,
    ):
        if left < edge < right:
            candidates.add(edge)
    return sorted(candidates)


def _prism_curve(prism: Prism, top: Elevation) -> Curve:
    """The prism as a function of offset, infinite where there is no prism."""

    def height(offset: float) -> float:
        try:
            return prism.design_elevation(offset, top).feet
        except MissingError:
            return math.inf

    return height


def section_area(
    before: Profile,
    after: Profile,
    prism: Prism,
    *,
    top: Elevation = DATUM,
) -> SectionArea:
    """Removed and pay areas at one station, in square feet."""
    if before.station != after.station:
        raise MissingError("matching station", f"{after.station}")
    breaks = _breaks(before, after, prism, top)
    prism_at = _prism_curve(prism, top)
    removed = 0.0
    pay = 0.0
    for x0, x1 in pairwise(breaks):
        b0, b1 = before.at(x0).feet, before.at(x1).feet
        a0, a1 = after.at(x0).feet, after.at(x1).feet
        removed += _positive_area(x0, x1, b0 - a0, b1 - a1)
        pay += _pay_area(x0, x1, (b0, b1), (a0, a1), (prism_at(x0), prism_at(x1)))
    return SectionArea(
        station=before.station,
        removed=round(removed, 4),
        pay=round(pay, 4),
        left=breaks[0],
        right=breaks[-1],
    )


def _pay_area(
    x0: float,
    x1: float,
    bed: tuple[float, float],
    cut: tuple[float, float],
    prism: tuple[float, float],
) -> float:
    """Area inside the prism over one interval, split at the floor's own kink."""
    if math.isinf(prism[0]) or math.isinf(prism[1]):
        return 0.0
    turn = _crossing(x0, x1, cut[0], cut[1], prism[0], prism[1])
    if turn is None:
        return _floor_area(x0, x1, bed, cut, prism)
    share = (turn - x0) / (x1 - x0)
    middle_bed = bed[0] + (bed[1] - bed[0]) * share
    middle_cut = cut[0] + (cut[1] - cut[0]) * share
    middle_prism = prism[0] + (prism[1] - prism[0]) * share
    return _floor_area(
        x0, turn, (bed[0], middle_bed), (cut[0], middle_cut), (prism[0], middle_prism)
    ) + _floor_area(turn, x1, (middle_bed, bed[1]), (middle_cut, cut[1]), (middle_prism, prism[1]))


def _floor_area(
    x0: float,
    x1: float,
    bed: tuple[float, float],
    cut: tuple[float, float],
    prism: tuple[float, float],
) -> float:
    """Area between the bed and whichever of the cut and the prism is higher."""
    floor0 = max(cut[0], prism[0])
    floor1 = max(cut[1], prism[1])
    return _positive_area(x0, x1, bed[0] - floor0, bed[1] - floor1)
