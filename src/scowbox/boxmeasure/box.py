"""Box measure.

Inside length by inside width by the mean depth of material, over twenty seven.
The whole method is one multiplication; everything else here is about whether
the four readings it rests on are worth multiplying.

Two things make a box measure worthless and neither of them shows up in the
answer. A light reading deeper than the box means the reference the crew
measured down from is not the one the box was measured to. And a scow with a
foot of trim across it is a wedge, not a box: the mean of four corners is still
arithmetically the mean, but the surface it describes is not flat and the
material under it is not a prism.
"""

from __future__ import annotations

from dataclasses import dataclass

from scowbox.errors import FieldError, RuleError
from scowbox.model.scow import BoxReading, Corner, Scow, ScowTrip
from scowbox.units.volume import Yards

MAX_TRIM_FEET = 2.0
MAX_HEEL_FEET = 1.0

BOW = (Corner.PORT_BOW, Corner.STARBOARD_BOW)
STERN = (Corner.PORT_STERN, Corner.STARBOARD_STERN)
PORT = (Corner.PORT_BOW, Corner.PORT_STERN)
STARBOARD = (Corner.STARBOARD_BOW, Corner.STARBOARD_STERN)


@dataclass(frozen=True)
class BoxMeasure:
    """One scow load, measured."""

    trip: str
    scow: str
    mean_material: float
    scow_yards: Yards
    share_full: float
    trim: float
    heel: float
    suspect: tuple[str, ...]

    @property
    def sound(self) -> bool:
        """True when nothing about the readings argues against using them."""
        return not self.suspect


def _mean(readings: dict[Corner, BoxReading], corners: tuple[Corner, ...]) -> float:
    return sum(readings[corner].material for corner in corners) / len(corners)


def measure(scow: Scow, trip: ScowTrip) -> BoxMeasure:
    """Measure one trip's load against the scow it was carried in."""
    if trip.scow != scow.ident:
        raise FieldError("scow", f"{trip.ident} was carried by {trip.scow}, not {scow.ident}")
    if not trip.measured:
        raise RuleError(f"{trip.ident} has no box readings")
    readings = {reading.corner: reading for reading in trip.readings}
    for reading in trip.readings:
        if reading.light > scow.inside_depth:
            raise RuleError(
                f"{trip.ident} reads {reading.light:g} ft light at the {reading.corner.value},"
                f" past the {scow.inside_depth:g} ft inside depth of {scow.ident}"
            )
    mean_material = round(sum(r.material for r in trip.readings) / len(trip.readings), 3)
    trim = round(_mean(readings, BOW) - _mean(readings, STERN), 3)
    heel = round(_mean(readings, PORT) - _mean(readings, STARBOARD), 3)
    suspect = []
    if abs(trim) > MAX_TRIM_FEET:
        suspect.append(f"trim {trim:+.2f} ft")
    if abs(heel) > MAX_HEEL_FEET:
        suspect.append(f"heel {heel:+.2f} ft")
    if mean_material <= 0:
        suspect.append("no material measured")
    return BoxMeasure(
        trip=trip.ident,
        scow=scow.ident,
        mean_material=mean_material,
        scow_yards=Yards.of_cubic_feet(scow.box_area * mean_material),
        share_full=round(mean_material / scow.inside_depth, 3),
        trim=trim,
        heel=heel,
        suspect=tuple(suspect),
    )
