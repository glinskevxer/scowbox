"""The plant on the job.

Three kinds of dredge turn up on maintenance work and they do not produce the
same records. A mechanical dredge fills scows, so it is measured by box. A
cutter suction dredge pumps ashore through a pipeline, so it is measured by
survey and its downtime includes moving the line. A hopper dredge carries its
own load and is measured either way depending on what the contract says.

The kind is therefore not decoration. It decides which records a shift is even
expected to produce, and a mechanical dredge working a shift with no scow trips
against it is a gap, where the same shift on a cutter is a normal day.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from scowbox.errors import FieldError
from scowbox.ids import is_ident


class Plant(Enum):
    """What kind of dredge it is."""

    MECHANICAL = "mechanical"
    CUTTER = "cutter suction"
    HOPPER = "hopper"

    @property
    def loads_scows(self) -> bool:
        return self is Plant.MECHANICAL

    @property
    def moves_pipeline(self) -> bool:
        return self is Plant.CUTTER


@dataclass(frozen=True)
class Dredge:
    """One dredge, as the contract names it."""

    ident: str
    name: str
    plant: Plant
    operator: str

    def __post_init__(self) -> None:
        if not is_ident("plant", self.ident):
            raise FieldError("ident", f"{self.ident!r} is not a plant identifier")
        if not self.name.strip():
            raise FieldError("name", "a dredge has a name")
        if not self.operator.strip():
            raise FieldError("operator", "a dredge is worked by somebody")

    def describe(self) -> str:
        return f"{self.ident} {self.name}, {self.plant.value}, {self.operator}"
