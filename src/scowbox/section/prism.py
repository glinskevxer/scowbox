"""The design surface at a station, and the pay prism under it.

A template drawn across the channel is a flat bottom of a given width, centred
on the centreline, with the sides laid back at the design slope. Three of them
sit one under another: the authorized cut, the required cut with advance
maintenance added, and the pay prism with the allowable overdepth added under
that.

The side slope carries all the way down. Overdepth is not a flat shelf under
the bottom; it is the whole template lowered, so its toe of slope steps out as
well as down. Getting that wrong overstates a wide shallow reach by more than
the overdepth allowance itself is worth.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from scowbox.errors import FieldError, MissingError
from scowbox.model.channel import Template
from scowbox.units.depth import Depth, Elevation


class Cut(Enum):
    """Which of the three depths a prism is drawn to."""

    AUTHORIZED = "authorized"
    REQUIRED = "required"
    PAY = "pay"


@dataclass(frozen=True)
class Prism:
    """The design surface across one station, drawn to one of the cuts."""

    bottom_width: float
    side_slope: float
    depth: Depth
    centre: float = 0.0

    @classmethod
    def of_template(cls, template: Template, cut: Cut, centre: float = 0.0) -> Prism:
        depths = {
            Cut.AUTHORIZED: template.authorized_depth,
            Cut.REQUIRED: template.required_depth,
            Cut.PAY: template.pay_depth,
        }
        return cls(
            bottom_width=template.bottom_width,
            side_slope=template.side_slope,
            depth=depths[cut],
            centre=centre,
        )

    @property
    def half_width(self) -> float:
        return self.bottom_width / 2

    @property
    def bottom(self) -> Elevation:
        return self.depth.elevation()

    @property
    def left_toe(self) -> float:
        return self.centre - self.half_width

    @property
    def right_toe(self) -> float:
        return self.centre + self.half_width

    def on_bottom(self, offset: float) -> bool:
        """True when the offset lies on the flat of the cut."""
        return self.left_toe <= offset <= self.right_toe

    def top_half_width(self, top: Elevation) -> float:
        """Half width where the design slope reaches an elevation."""
        rise = top - self.bottom
        if rise < 0:
            raise FieldError("top", "the top of a prism lies above its bottom")
        if self.side_slope == 0:
            return self.half_width
        return self.half_width + self.side_slope * rise

    def design_elevation(self, offset: float, top: Elevation) -> Elevation:
        """The design surface at an offset, up to the given top of slope."""
        away = abs(offset - self.centre)
        if away <= self.half_width:
            return self.bottom
        if self.side_slope == 0:
            raise MissingError("prism at offset", f"{offset:g}")
        raised = self.bottom.raised((away - self.half_width) / self.side_slope)
        if raised.above(top):
            raise MissingError("prism at offset", f"{offset:g}")
        return raised

    def lowered(self, feet: float) -> Prism:
        """The same template cut deeper, sides carried down with it."""
        return Prism(
            bottom_width=self.bottom_width,
            side_slope=self.side_slope,
            depth=self.depth.below(feet),
            centre=self.centre,
        )

    def area_to(self, top: Elevation) -> float:
        """Cross section area of the prism between its bottom and a flat top.

        The trapezoid a template makes: bottom width by height, plus the two
        side triangles.
        """
        height = top - self.bottom
        if height <= 0:
            return 0.0
        return self.bottom_width * height + self.side_slope * height * height
