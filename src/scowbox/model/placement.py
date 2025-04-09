"""Where the material goes.

Three kinds of ground take dredged material and they do not take the same
material. An ocean site takes what the sediment testing found suitable for
ocean placement. A confined disposal facility takes anything, which is what it
is for, and it is the only one with a capacity that runs out. A beach template
takes sand of the grain size the permit specifies and nothing else, because
what is placed there is what people stand on.

The permit number is on the record because every one of these is a permitted
activity and a ticket that cannot be traced to a permit is a finding.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from enum import Enum

from scowbox.errors import FieldError
from scowbox.ids import is_ident
from scowbox.units.clock import aware
from scowbox.units.volume import Yards


class Grade(Enum):
    """What the sediment testing found."""

    SUITABLE = "suitable"
    UNSUITABLE = "unsuitable"
    BEACH_QUALITY = "beach quality"


class Ground(Enum):
    """The kind of place, which decides what it may take."""

    OCEAN = "ocean site"
    UPLAND = "confined disposal"
    BEACH = "beach nourishment"

    @property
    def takes(self) -> frozenset[Grade]:
        if self is Ground.OCEAN:
            return frozenset({Grade.SUITABLE, Grade.BEACH_QUALITY})
        if self is Ground.BEACH:
            return frozenset({Grade.BEACH_QUALITY})
        return frozenset(Grade)

    @property
    def fills(self) -> bool:
        """True when the ground has a capacity that can run out."""
        return self is Ground.UPLAND


@dataclass(frozen=True)
class PlacementArea:
    """One permitted place to put material."""

    ident: str
    name: str
    ground: Ground
    permit: str
    capacity: Yards | None = None

    def __post_init__(self) -> None:
        if not is_ident("placement", self.ident):
            raise FieldError("ident", f"{self.ident!r} is not a placement identifier")
        if not self.name.strip():
            raise FieldError("name", "a placement area has a name")
        if not self.permit.strip():
            raise FieldError("permit", "a placement area is placed under a permit")
        if self.ground.fills and self.capacity is None:
            raise FieldError("capacity", f"a {self.ground.value} has a capacity")
        if self.capacity is not None and self.capacity.hundredths <= 0:
            raise FieldError("capacity", "a capacity is a volume")

    def takes(self, grade: Grade) -> bool:
        return grade in self.ground.takes


@dataclass(frozen=True)
class PlacementTicket:
    """One load released at one place, at one time."""

    trip: str
    area: str
    released: dt.datetime
    yards: Yards
    grade: Grade

    def __post_init__(self) -> None:
        if not is_ident("trip", self.trip):
            raise FieldError("trip", f"{self.trip!r} is not a trip identifier")
        if not is_ident("placement", self.area):
            raise FieldError("area", f"{self.area!r} is not a placement identifier")
        aware(self.released)
        if self.yards.hundredths <= 0:
            raise FieldError("yards", "a ticket carries a load")
