"""Scows, their boxes, and the trips they make.

A mechanical dredge does not measure what it digs. It fills a scow, and the
scow is measured. The measurement is a box: inside length by inside width by
the mean depth of material, and the mean depth comes from readings taken down
from a fixed reference at the four corners.

Four corners, not one amidships. A scow under a bucket loads unevenly and takes
a trim and a list doing it. One reading in the middle of a scow trimmed by the
stern reads the average of nothing.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from enum import Enum

from scowbox.errors import FieldError, RangeError
from scowbox.ids import is_ident

MAX_BOX_FEET = 400.0
MAX_DEPTH_FEET = 40.0


class Corner(Enum):
    """Where a box reading is taken. All four, every time."""

    PORT_BOW = "port bow"
    STARBOARD_BOW = "starboard bow"
    PORT_STERN = "port stern"
    STARBOARD_STERN = "starboard stern"


@dataclass(frozen=True)
class Scow:
    """One scow, measured inside the coaming."""

    ident: str
    name: str
    inside_length: float
    inside_width: float
    inside_depth: float

    def __post_init__(self) -> None:
        if not is_ident("scow", self.ident):
            raise FieldError("ident", f"{self.ident!r} is not a scow identifier")
        if not self.name.strip():
            raise FieldError("name", "a scow has a name")
        for label, value, ceiling in (
            ("inside_length", self.inside_length, MAX_BOX_FEET),
            ("inside_width", self.inside_width, MAX_BOX_FEET),
            ("inside_depth", self.inside_depth, MAX_DEPTH_FEET),
        ):
            if not 0 < value <= ceiling:
                raise RangeError(label, value, 0, ceiling)

    @property
    def box_area(self) -> float:
        """Plan area of the box in square feet."""
        return self.inside_length * self.inside_width

    def describe(self) -> str:
        return (
            f"{self.ident} {self.name}, {self.inside_length:g} by {self.inside_width:g}"
            f" by {self.inside_depth:g} ft inside"
        )


@dataclass(frozen=True)
class BoxReading:
    """One corner, light and loaded, measured down from the reference."""

    corner: Corner
    light: float
    loaded: float

    def __post_init__(self) -> None:
        for label, value in (("light", self.light), ("loaded", self.loaded)):
            if value < 0:
                raise FieldError(label, "a box reading is measured downward and is not negative")
        if self.loaded > self.light:
            raise FieldError(
                "loaded",
                f"loaded reads {self.loaded:g} ft, further down than light at {self.light:g} ft",
            )

    @property
    def material(self) -> float:
        """Depth of material under this corner, in feet."""
        return round(self.light - self.loaded, 3)


@dataclass(frozen=True)
class ScowTrip:
    """One scow load, from the reach it came out of to where it went."""

    ident: str
    scow: str
    reach: str
    loaded_on: dt.date
    placement: str
    readings: tuple[BoxReading, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not is_ident("trip", self.ident):
            raise FieldError("ident", f"{self.ident!r} is not a trip identifier")
        if not is_ident("scow", self.scow):
            raise FieldError("scow", f"{self.scow!r} is not a scow identifier")
        if not is_ident("reach", self.reach):
            raise FieldError("reach", f"{self.reach!r} is not a reach identifier")
        if not is_ident("placement", self.placement):
            raise FieldError("placement", f"{self.placement!r} is not a placement identifier")
        if self.readings:
            corners = [r.corner for r in self.readings]
            if len(set(corners)) != len(Corner) or len(corners) != len(Corner):
                raise FieldError("readings", "a box measure takes all four corners, once each")

    @property
    def measured(self) -> bool:
        return bool(self.readings)

    def with_readings(self, readings: tuple[BoxReading, ...]) -> ScowTrip:
        """A copy carrying a box measure."""
        return ScowTrip(
            ident=self.ident,
            scow=self.scow,
            reach=self.reach,
            loaded_on=self.loaded_on,
            placement=self.placement,
            readings=readings,
        )
