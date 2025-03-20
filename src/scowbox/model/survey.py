"""Hydrographic surveys and the soundings in them.

A survey is one pass of a vessel over one reach on one day. Each sounding is a
raw transducer reading at a station and an offset from the channel centreline,
positive to the right looking ahead. Nothing in this module reduces a reading
to datum; that needs the tide, and the tide is not part of the record.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from enum import Enum

from scowbox.errors import FieldError, RangeError
from scowbox.ids import is_ident
from scowbox.units.clock import aware
from scowbox.units.depth import Depth
from scowbox.units.station import Station

MAX_OFFSET_FEET = 2000.0
MAX_DRAFT_FEET = 12.0


class SurveyKind(Enum):
    """What the survey is for, which decides what it may be used to prove."""

    BEFORE = "before"
    PROGRESS = "progress"
    AFTER = "after"
    SWEEP = "sweep"

    @property
    def pays(self) -> bool:
        """A progress survey informs. Only a before and an after pay."""
        return self in (SurveyKind.BEFORE, SurveyKind.AFTER)


@dataclass(frozen=True)
class Sounding:
    """One transducer reading, uncorrected."""

    station: Station
    offset: float
    raw_depth: Depth
    taken: dt.datetime

    def __post_init__(self) -> None:
        if abs(self.offset) > MAX_OFFSET_FEET:
            raise RangeError("offset", self.offset, -MAX_OFFSET_FEET, MAX_OFFSET_FEET)
        if self.raw_depth.hundredths <= 0:
            raise FieldError("raw_depth", "a transducer reads a depth below itself")
        aware(self.taken)


@dataclass(frozen=True)
class Survey:
    """One pass over one reach, on one day, by one vessel."""

    ident: str
    reach: str
    kind: SurveyKind
    taken_on: dt.date
    vessel: str
    transducer_draft: float
    gauge: str = ""
    soundings: tuple[Sounding, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not is_ident("survey", self.ident):
            raise FieldError("ident", f"{self.ident!r} is not a survey identifier")
        if not is_ident("reach", self.reach):
            raise FieldError("reach", f"{self.reach!r} is not a reach identifier")
        if not self.vessel.strip():
            raise FieldError("vessel", "a survey names the vessel that ran it")
        if not 0 < self.transducer_draft <= MAX_DRAFT_FEET:
            raise RangeError("transducer_draft", self.transducer_draft, 0, MAX_DRAFT_FEET)

    @property
    def reduces(self) -> bool:
        """True when the survey names the gauge its shots reduce against."""
        return bool(self.gauge.strip())

    @property
    def count(self) -> int:
        return len(self.soundings)

    def stations(self) -> tuple[Station, ...]:
        """The distinct stations sounded, in order along the channel."""
        return tuple(sorted({s.station for s in self.soundings}))

    def at_station(self, station: Station) -> tuple[Sounding, ...]:
        """Every sounding on one station, ordered left to right across it."""
        here = [s for s in self.soundings if s.station == station]
        return tuple(sorted(here, key=lambda s: s.offset))

    def with_soundings(self, soundings: tuple[Sounding, ...]) -> Survey:
        """A copy carrying these soundings. Records are frozen; loading is not."""
        return Survey(
            ident=self.ident,
            reach=self.reach,
            kind=self.kind,
            taken_on=self.taken_on,
            vessel=self.vessel,
            transducer_draft=self.transducer_draft,
            gauge=self.gauge,
            soundings=soundings,
        )
