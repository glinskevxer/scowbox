"""Contract modifications.

A dredging contract is modified. The channel turns out to hold rock, an
environmental window moves, a reach is added, a price is renegotiated. Each of
those is a signed document with a number, and every one of them changes what
the estimates are computed against from its effective date onward.

The record here is one modification and what it changes. Applying it is the
next module's job, and applying them in order is the whole of it: two
modifications that both touch the same unit price mean the later one wins, and
a program that applies them in whatever order the rows came back in has an
estimate that changes when the database is vacuumed.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from enum import Enum

from scowbox.errors import FieldError
from scowbox.ids import is_ident
from scowbox.units.money import Money


class Change(Enum):
    """What a modification changes."""

    TIME = "contract time"
    PRICE = "unit price"
    ITEM = "new line item"

    @property
    def needs_days(self) -> bool:
        return self is Change.TIME

    @property
    def needs_item(self) -> bool:
        return self in (Change.PRICE, Change.ITEM)

    @property
    def needs_price(self) -> bool:
        return self in (Change.PRICE, Change.ITEM)


@dataclass(frozen=True)
class Modification:
    """One signed modification to the contract."""

    number: str
    signed_on: dt.date
    change: Change
    description: str
    days: int = 0
    item: str = ""
    price: Money | None = None

    def __post_init__(self) -> None:
        if not self.number.strip():
            raise FieldError("number", "a modification is numbered")
        if not self.description.strip():
            raise FieldError("description", "a modification says what it did")
        if self.change.needs_days and self.days == 0:
            raise FieldError("days", "a time extension is some days")
        if not self.change.needs_days and self.days != 0:
            raise FieldError("days", f"a {self.change.value} modification changes no days")
        if self.change.needs_item and not is_ident("item", self.item):
            raise FieldError("item", f"{self.item!r} is not a line item identifier")
        if not self.change.needs_item and self.item:
            raise FieldError("item", f"a {self.change.value} modification names no item")
        if self.change.needs_price:
            if self.price is None:
                raise FieldError("price", f"a {self.change.value} modification carries a price")
            if self.price.cents <= 0:
                raise FieldError("price", "a unit price is above nothing")
        elif self.price is not None:
            raise FieldError("price", f"a {self.change.value} modification carries no price")

    def describe(self) -> str:
        what = {
            Change.TIME: f"{self.days:+,} days",
            Change.PRICE: f"{self.item} at {self.price}",
            Change.ITEM: f"{self.item} at {self.price}",
        }[self.change]
        return f"{self.number} ({self.signed_on}) {self.change.value}: {what}"
