"""The contract: what is being paid for, and on what terms.

A bid schedule is a short list. Cubic yards of dredging in each pay group, a
lump sum for mobilisation and demobilisation, and a day rate for whatever the
specification puts on standby. The three are priced in different units and a
schedule that treats them alike is a schedule that will extend a lump sum by a
quantity of cubic yards.

Contract time is calendar days from the notice to proceed. Liquidated damages
are a fixed amount per day past it, and they are not a penalty the office gets
to argue about: they are arithmetic, which is exactly why they are here.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from enum import Enum

from scowbox.errors import DuplicateError, FieldError, MissingError, RangeError
from scowbox.ids import is_ident
from scowbox.units.money import Money

MAX_RETAINAGE = 0.10


class Unit(Enum):
    """What a line item is priced by."""

    CUBIC_YARD = "cy"
    LUMP_SUM = "ls"
    DAY = "day"

    @property
    def by_quantity(self) -> bool:
        """True when the item is extended by a measured quantity."""
        return self is Unit.CUBIC_YARD


@dataclass(frozen=True)
class LineItem:
    """One line of the bid schedule."""

    ident: str
    description: str
    unit: Unit
    unit_price: Money
    group: str = ""
    estimated: float = 0.0

    def __post_init__(self) -> None:
        if not is_ident("item", self.ident):
            raise FieldError("ident", f"{self.ident!r} is not a line item identifier")
        if not self.description.strip():
            raise FieldError("description", "a line item says what it is for")
        if self.unit_price.cents <= 0:
            raise FieldError("unit_price", "a line item is priced above nothing")
        if self.estimated < 0:
            raise FieldError("estimated", "a bid quantity is not negative")
        if self.unit.by_quantity and not self.group.strip():
            raise FieldError("group", "a cubic yard item is billed for a pay group")
        if not self.unit.by_quantity and self.group.strip():
            raise FieldError("group", f"a {self.unit.value} item has no pay group")


@dataclass(frozen=True)
class Contract:
    """The contract the estimates are written against."""

    number: str
    awarded: dt.date
    notice_to_proceed: dt.date
    days: int
    retainage: float
    liquidated: Money
    items: tuple[LineItem, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.number.strip():
            raise FieldError("number", "a contract has a number")
        if self.notice_to_proceed < self.awarded:
            raise FieldError("notice_to_proceed", "notice to proceed follows award")
        if self.days <= 0:
            raise FieldError("days", "a contract runs for some days")
        if not 0 <= self.retainage <= MAX_RETAINAGE:
            raise RangeError("retainage", self.retainage, 0, MAX_RETAINAGE)
        if self.liquidated.cents < 0:
            raise FieldError("liquidated", "liquidated damages are not a credit")
        idents = [item.ident for item in self.items]
        if len(set(idents)) != len(idents):
            raise DuplicateError("line item", "in the same contract")
        groups = [item.group for item in self.items if item.unit.by_quantity]
        if len(set(groups)) != len(groups):
            raise DuplicateError("pay group", "on two cubic yard items")

    @property
    def completion(self) -> dt.date:
        """The day the work is due, before any time extension."""
        return self.notice_to_proceed + dt.timedelta(days=self.days)

    def item(self, ident: str) -> LineItem:
        for line in self.items:
            if line.ident == ident:
                return line
        raise MissingError("line item", ident)

    def for_group(self, group: str) -> LineItem:
        """The cubic yard item a pay group bills against."""
        for line in self.items:
            if line.unit.by_quantity and line.group == group:
                return line
        raise MissingError("line item for pay group", group)

    def days_late(self, finished: dt.date, extension: int = 0) -> int:
        """Days past completion, counting a time extension in the contractor's favour."""
        due = self.completion + dt.timedelta(days=extension)
        return max((finished - due).days, 0)
