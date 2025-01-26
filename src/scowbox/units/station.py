"""Channel stationing.

Distance along a channel centreline is written in stations of one hundred feet.
Station ``12+50.25`` is 1250.25 feet from the start of the channel. Surveyors
write it that way, contract drawings label it that way, and a pay estimate that
prints 1250.25 instead is one a project engineer has to translate before they
can check it against the plans.

Held as whole hundredths of a foot. Section intervals, template widths and
overdepth allowances are all given to the hundredth, and a float sum of two
hundred of them drifts far enough to move a section boundary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Self

from scowbox.errors import FieldError

_TEXT = re.compile(r"^(-?[0-9]+)\+([0-9]{2}(?:\.[0-9]{1,2})?)$")


@dataclass(frozen=True, order=True)
class Station:
    """A point on the channel centreline, in hundredths of a foot."""

    hundredths: int

    @classmethod
    def of_feet(cls, feet: float) -> Self:
        """Build a station from a distance in feet, rounded to the hundredth."""
        return cls(round(feet * 100))

    @classmethod
    def parse(cls, text: str) -> Self:
        """Read surveyor notation such as ``12+50`` or ``12+50.25``."""
        match = _TEXT.match(text.strip())
        if match is None:
            raise FieldError("station", f"{text!r} is not stationing such as 12+50")
        whole, rest = match.group(1), match.group(2)
        sign = -1 if whole.startswith("-") else 1
        hundreds = abs(int(whole))
        return cls(sign * (hundreds * 10000 + round(float(rest) * 100)))

    @property
    def feet(self) -> float:
        """The distance in feet, for arithmetic that has left the domain."""
        return self.hundredths / 100

    def __str__(self) -> str:
        sign = "-" if self.hundredths < 0 else ""
        whole = abs(self.hundredths)
        hundreds, rest = divmod(whole, 10000)
        if rest % 100 == 0:
            return f"{sign}{hundreds}+{rest // 100:02d}"
        return f"{sign}{hundreds}+{rest / 100:05.2f}"

    def __add__(self, feet: float) -> Station:
        return Station(self.hundredths + round(feet * 100))

    def __sub__(self, other: Station) -> float:
        return (self.hundredths - other.hundredths) / 100


@dataclass(frozen=True)
class Reachline:
    """A run of channel between two stations, ahead station last."""

    begin: Station
    end: Station

    def __post_init__(self) -> None:
        if self.end.hundredths <= self.begin.hundredths:
            raise FieldError("station range", f"{self.end} does not lie ahead of {self.begin}")

    @classmethod
    def parse(cls, begin: str, end: str) -> Self:
        """Build a run from two pieces of surveyor notation."""
        return cls(Station.parse(begin), Station.parse(end))

    @property
    def length(self) -> float:
        """Length of the run in feet."""
        return self.end - self.begin

    def holds(self, station: Station) -> bool:
        """True when the station lies in the run, ahead station excluded."""
        return self.begin.hundredths <= station.hundredths < self.end.hundredths

    def overlaps(self, other: Reachline) -> bool:
        """True when the two runs share any length at all."""
        return self.begin.hundredths < other.end.hundredths and (
            other.begin.hundredths < self.end.hundredths
        )

    def cuts(self, interval: float) -> list[Station]:
        """Section stations every ``interval`` feet, both ends included.

        The last interval is short when the run does not divide evenly. It is
        not stretched and it is not dropped: average end area needs the real
        length between the last two sections.
        """
        step = round(interval * 100)
        if step <= 0:
            raise FieldError("interval", "section interval must be positive")
        cuts = []
        at = self.begin.hundredths
        while at < self.end.hundredths:
            cuts.append(Station(at))
            at += step
        cuts.append(self.end)
        return cuts

    def __str__(self) -> str:
        return f"{self.begin} to {self.end}"
