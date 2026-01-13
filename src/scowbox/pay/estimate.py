"""The monthly progress estimate.

Earned to date, less retainage, less liquidated damages, less everything paid
before: that is the cheque. Each of those four is worked out on the cumulative
figure, so an estimate stands on its own and a revision to an earlier month
flows through without anybody re-adding a column.

Retainage comes off the earned amount, not off the amount due. Taking it off
the difference would retain five percent of one month's work rather than five
percent of the job, which is a different and much smaller number.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping
from dataclasses import dataclass, field

from scowbox.errors import FieldError, MissingError
from scowbox.ids import is_ident
from scowbox.model.contract import Contract, LineItem, Unit
from scowbox.units.money import Money, half_up, total
from scowbox.units.volume import Yards

NOTHING = Money(0)
"""A zero amount, named once so it is not rebuilt in a dataclass default."""


@dataclass(frozen=True)
class EstimateLine:
    """One line of one estimate, always cumulative."""

    item: str
    description: str
    unit: Unit
    unit_price: Money
    to_date: float
    previous: float = 0.0

    def __post_init__(self) -> None:
        if self.to_date < 0 or self.previous < 0:
            raise FieldError("to_date", "an estimate line does not carry a negative quantity")
        if self.unit is Unit.LUMP_SUM and self.to_date > 1:
            raise FieldError("to_date", "a lump sum is complete at one, not at more")

    @property
    def this_period(self) -> float:
        return round(self.to_date - self.previous, 4)

    @property
    def earned(self) -> Money:
        return Money(half_up(self.unit_price.cents * self.to_date))

    @property
    def earned_before(self) -> Money:
        return Money(half_up(self.unit_price.cents * self.previous))

    @property
    def earned_this_period(self) -> Money:
        return self.earned - self.earned_before


@dataclass(frozen=True)
class Estimate:
    """One monthly progress estimate."""

    ident: str
    contract: str
    number: int
    through: dt.date
    retainage: float
    lines: tuple[EstimateLine, ...] = field(default_factory=tuple)
    days_late: int = 0
    liquidated_rate: Money = NOTHING
    paid_before: Money = NOTHING
    final: bool = False

    def __post_init__(self) -> None:
        if not is_ident("estimate", self.ident):
            raise FieldError("ident", f"{self.ident!r} is not an estimate identifier")
        if self.number <= 0:
            raise FieldError("number", "estimates are numbered from one")
        if self.days_late < 0:
            raise FieldError("days_late", "days late are counted forward")

    @property
    def earned(self) -> Money:
        return total(line.earned for line in self.lines)

    @property
    def retained(self) -> Money:
        """Retainage still withheld. The final estimate releases all of it."""
        if self.final:
            return NOTHING
        return self.earned.portion(self.retainage)

    @property
    def released(self) -> Money:
        """Retainage handed back on this estimate, which is only ever the last."""
        if not self.final:
            return NOTHING
        return self.earned.portion(self.retainage)

    @property
    def liquidated(self) -> Money:
        return Money(self.liquidated_rate.cents * self.days_late)

    @property
    def payable(self) -> Money:
        """Everything due to date, before what has already been paid."""
        return self.earned - self.retained - self.liquidated

    @property
    def due(self) -> Money:
        """The cheque this month."""
        return self.payable - self.paid_before

    def line(self, item: str) -> EstimateLine:
        for found in self.lines:
            if found.item == item:
                return found
        raise MissingError("estimate line", item)


def _line(item: LineItem, to_date: float, previous: float) -> EstimateLine:
    return EstimateLine(
        item=item.ident,
        description=item.description,
        unit=item.unit,
        unit_price=item.unit_price,
        to_date=to_date,
        previous=previous,
    )


def build(
    contract: Contract,
    number: int,
    through: dt.date,
    quantities: Mapping[str, Yards],
    others: Mapping[str, float] | None = None,
    previous: Estimate | None = None,
    *,
    days_late: int = 0,
    final: bool = False,
) -> Estimate:
    """Build an estimate from quantities by pay group and shares by line item.

    Every line item in the contract appears, whether or not anything was earned
    against it. An estimate that drops its empty lines is one the owner cannot
    lay alongside last month's.
    """
    standing = others or {}
    lines = []
    for item in contract.items:
        if item.unit.by_quantity:
            found = quantities.get(item.group)
            to_date = 0.0 if found is None else found.yards
        else:
            to_date = float(standing.get(item.ident, 0.0))
        before = 0.0
        if previous is not None:
            try:
                before = previous.line(item.ident).to_date
            except MissingError:
                before = 0.0
        lines.append(_line(item, to_date, before))
    return Estimate(
        ident=f"EST-{number:03d}",
        contract=contract.number,
        number=number,
        through=through,
        retainage=contract.retainage,
        lines=tuple(lines),
        days_late=days_late,
        liquidated_rate=contract.liquidated,
        paid_before=NOTHING if previous is None else previous.payable,
        final=final,
    )
