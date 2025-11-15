"""Reconciliation: what the parties agreed when the measurements did not.

A reach measured both ways and disagreeing past the tolerance is paid on the
lesser of the two, on account, and somebody has to go and work out why. What
comes back is one of three answers. The survey was right. The scows were right.
Or neither was, and a figure was agreed between them.

The record is deliberately heavy. It names who decided, on what day, and what
they were looking at, because a reconciliation is the one place on the job
where a quantity is set by agreement rather than by measurement, and six months
later somebody will ask.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from enum import Enum

from scowbox.errors import FieldError
from scowbox.ids import is_ident
from scowbox.units.volume import Yards


class Accepted(Enum):
    """Which answer the reconciliation settled on."""

    SURVEY = "survey"
    SCOW = "scow"
    AGREED = "agreed figure"

    @property
    def needs_quantity(self) -> bool:
        """True when the record has to carry a figure of its own."""
        return self is Accepted.AGREED


@dataclass(frozen=True)
class Reconciliation:
    """One settled disagreement over one reach."""

    reach: str
    decided_on: dt.date
    accepted: Accepted
    decided_by: str
    note: str = ""
    quantity: Yards | None = None

    def __post_init__(self) -> None:
        if not is_ident("reach", self.reach):
            raise FieldError("reach", f"{self.reach!r} is not a reach identifier")
        if not self.decided_by.strip():
            raise FieldError("decided_by", "a reconciliation names who decided it")
        if self.accepted.needs_quantity:
            if self.quantity is None:
                raise FieldError("quantity", "an agreed figure is a figure")
            if self.quantity.hundredths < 0:
                raise FieldError("quantity", "an agreed figure is not negative")
            if not self.note.strip():
                raise FieldError("note", "an agreed figure says what it was agreed on")
        elif self.quantity is not None:
            raise FieldError(
                "quantity",
                f"accepting the {self.accepted.value} takes that figure, not another",
            )

    def describe(self) -> str:
        figure = f", {self.quantity.rounded()}" if self.quantity is not None else ""
        return (
            f"{self.reach} settled {self.decided_on} by {self.decided_by}:"
            f" {self.accepted.value}{figure}"
        )
