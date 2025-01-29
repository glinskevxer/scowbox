"""The channel: reaches, and the template each one is dredged to.

A federal navigation channel is cut into reaches, and each reach has a template
that says how wide the bottom is, how deep it is cut below the tidal datum, and
how the sides lay back. Three depths come off that template and they are not
interchangeable:

    authorized  what Congress authorised and the drawings label
    required    authorized plus advance maintenance, what the contract digs to
    pay         required plus the allowable overdepth, the bottom of the prism

Material above the pay depth is paid for. Material below it was still removed,
and the contractor still hauled it, and nobody pays for it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from scowbox.errors import FieldError, RangeError
from scowbox.ids import is_ident
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline

MAX_ADVANCE_FEET = 4.0
MAX_OVERDEPTH_FEET = 4.0
MAX_SIDE_SLOPE = 10.0


class Method(Enum):
    """How a reach's pay quantity is measured."""

    SURVEY = "survey"
    SCOW = "scow"
    BOTH = "both"

    @property
    def takes_survey(self) -> bool:
        return self in (Method.SURVEY, Method.BOTH)

    @property
    def takes_scow(self) -> bool:
        return self in (Method.SCOW, Method.BOTH)


@dataclass(frozen=True)
class Template:
    """The cut a reach is dredged to."""

    bottom_width: float
    authorized_depth: Depth
    side_slope: float
    advance_maintenance: float = 0.0
    overdepth: float = 0.0

    def __post_init__(self) -> None:
        if self.bottom_width <= 0:
            raise FieldError("bottom_width", "a template needs a bottom")
        if not 0 <= self.side_slope <= MAX_SIDE_SLOPE:
            raise RangeError("side_slope", self.side_slope, 0, MAX_SIDE_SLOPE)
        if not 0 <= self.advance_maintenance <= MAX_ADVANCE_FEET:
            raise RangeError("advance_maintenance", self.advance_maintenance, 0, MAX_ADVANCE_FEET)
        if not 0 <= self.overdepth <= MAX_OVERDEPTH_FEET:
            raise RangeError("overdepth", self.overdepth, 0, MAX_OVERDEPTH_FEET)

    @property
    def required_depth(self) -> Depth:
        """What the contract digs to."""
        return self.authorized_depth.below(self.advance_maintenance)

    @property
    def pay_depth(self) -> Depth:
        """The bottom of the pay prism."""
        return self.required_depth.below(self.overdepth)

    @property
    def top_width(self) -> float:
        """Width at the pay depth's top of slope, for a first look at the cut."""
        return self.bottom_width + 2 * self.side_slope * self.pay_depth.feet

    def describe(self) -> str:
        return (
            f"{self.bottom_width:g} ft bottom, {self.required_depth} required"
            f" plus {self.overdepth:g} ft overdepth, {self.side_slope:g}:1 side slope"
        )


@dataclass(frozen=True)
class Reach:
    """A stationed length of channel dredged to one template."""

    ident: str
    name: str
    line: Reachline
    template: Template
    method: Method = Method.SURVEY
    group: str = "base"

    def __post_init__(self) -> None:
        if not is_ident("reach", self.ident):
            raise FieldError("ident", f"{self.ident!r} is not a reach identifier")
        if not self.name.strip():
            raise FieldError("name", "a reach needs a name")
        if not self.group.strip():
            raise FieldError("group", "a reach belongs to a pay item group")

    @property
    def length(self) -> float:
        return self.line.length

    def adjoins(self, other: Reach) -> bool:
        """True when the two reaches meet end to end with no gap."""
        return self.line.end == other.line.begin or other.line.end == self.line.begin

    def describe(self) -> str:
        return f"{self.ident} {self.name}, {self.line}, {self.template.describe()}"
