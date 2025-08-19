"""Bulking.

Material in a scow occupies more room than the same material did in the bed.
The ratio is the bulking factor, and it is the number on a dredging contract
with the widest honest range: a stiff clay comes up in lumps with voids between
them and bulks half again, a clean sand barely bulks at all.

So the factor is a property of the contract and the material, not of this
program. What lives here is the arithmetic and the range beyond which a factor
is a typing error rather than a soil.
"""

from __future__ import annotations

from dataclasses import dataclass

from scowbox.errors import MissingError, RangeError
from scowbox.units.volume import Yards

MIN_FACTOR = 1.0
MAX_FACTOR = 1.75


@dataclass(frozen=True)
class Bulking:
    """The factor for one material class, as the contract states it."""

    material: str
    factor: float

    def __post_init__(self) -> None:
        if not MIN_FACTOR <= self.factor <= MAX_FACTOR:
            raise RangeError("factor", self.factor, MIN_FACTOR, MAX_FACTOR)

    def in_place(self, scow_yards: Yards) -> Yards:
        """Turn scow yards back into the yards the bed lost."""
        return scow_yards.scaled(1 / self.factor)

    def in_scow(self, place_yards: Yards) -> Yards:
        """Turn bed yards into the room they take up in a scow."""
        return place_yards.scaled(self.factor)


TYPICAL: tuple[Bulking, ...] = (
    Bulking("sand", 1.05),
    Bulking("silt", 1.20),
    Bulking("clay", 1.45),
    Bulking("mixed", 1.25),
)

_BY_MATERIAL = {b.material: b for b in TYPICAL}


def typical(material: str) -> Bulking:
    """A starting factor for a material, for use until the contract states one."""
    try:
        return _BY_MATERIAL[material]
    except KeyError:
        raise MissingError("bulking factor for", material) from None


def materials() -> tuple[str, ...]:
    """Every material a starting factor is published for."""
    return tuple(b.material for b in TYPICAL)
