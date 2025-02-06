"""Reducing a raw sounding to the datum.

Four numbers stand between the echo sounder and the contract:

    tide    height of the water surface above datum at the moment of the shot
    draft   how far the transducer sits below that surface at rest
    squat   how much further it sits at survey speed
    index   the bar check correction applied to the reading itself

Bed elevation is the water surface, less the transducer's own depth, less what
the transducer read. Every one of those four has been the cause of a survey
being thrown out on this coast, so each of them is named and each of them is
carried separately rather than pre-added into a single fudge.
"""

from __future__ import annotations

from dataclasses import dataclass

from scowbox.datum.tide import TideRecord
from scowbox.errors import RangeError
from scowbox.model.survey import Sounding, Survey
from scowbox.units.depth import Depth, Elevation
from scowbox.units.station import Station

MAX_SQUAT_FEET = 2.0
MAX_INDEX_FEET = 1.0


@dataclass(frozen=True)
class Correction:
    """Everything applied to a reading that is not the tide."""

    draft: float
    squat: float = 0.0
    index: float = 0.0

    def __post_init__(self) -> None:
        if not 0 < self.draft <= 12:
            raise RangeError("draft", self.draft, 0, 12)
        if not 0 <= self.squat <= MAX_SQUAT_FEET:
            raise RangeError("squat", self.squat, 0, MAX_SQUAT_FEET)
        if abs(self.index) > MAX_INDEX_FEET:
            raise RangeError("index", self.index, -MAX_INDEX_FEET, MAX_INDEX_FEET)

    @property
    def transducer_below_surface(self) -> float:
        """How far under the water surface the head is while running."""
        return self.draft + self.squat


@dataclass(frozen=True)
class Shot:
    """A sounding once it is on the datum."""

    station: Station
    offset: float
    bed: Elevation

    @property
    def depth(self) -> Depth:
        """The same point as a depth below datum, which is how a template reads."""
        return self.bed.depth()


def bed_elevation(raw: Depth, tide_height: float, correction: Correction) -> Elevation:
    """Put one reading on the datum."""
    surface = tide_height
    head = surface - correction.transducer_below_surface
    return Elevation.of_feet(head - (raw.feet + correction.index))


def reduce_one(sounding: Sounding, tide_height: float, correction: Correction) -> Shot:
    """Reduce a single sounding against a tide height already looked up."""
    return Shot(
        station=sounding.station,
        offset=sounding.offset,
        bed=bed_elevation(sounding.raw_depth, tide_height, correction),
    )


def reduce_survey(
    survey: Survey,
    tide: TideRecord,
    *,
    squat: float = 0.0,
    index: float = 0.0,
) -> tuple[Shot, ...]:
    """Reduce every sounding in a survey against the gauge that covered it.

    The draft comes off the survey record, because it is a property of the
    vessel that ran it. Squat and index come from the calibration for that day
    and are passed in.
    """
    correction = Correction(draft=survey.transducer_draft, squat=squat, index=index)
    return tuple(
        reduce_one(sounding, tide.height_at(sounding.taken), correction)
        for sounding in survey.soundings
    )
