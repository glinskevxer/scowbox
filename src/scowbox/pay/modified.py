"""The contract as modified.

Modifications are applied in signature order, oldest first, and the last word
on any one thing wins. Nothing is applied twice and nothing is applied out of
order, which are the two ways a schedule of values stops tying to the file.

A modification that adds a line item the contract already has is a finding
rather than a silent replacement: somebody has either numbered two documents
the same way or meant to change a price and picked the wrong kind.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from scowbox.errors import RuleError
from scowbox.model.contract import Contract, LineItem, Unit
from scowbox.model.modification import Change, Modification


@dataclass(frozen=True)
class Modified:
    """A contract, the modifications applied to it, and what they did."""

    contract: Contract
    applied: tuple[Modification, ...]
    added_days: int

    @property
    def count(self) -> int:
        return len(self.applied)

    @property
    def numbers(self) -> tuple[str, ...]:
        return tuple(m.number for m in self.applied)


def in_order(modifications: Iterable[Modification]) -> tuple[Modification, ...]:
    """Modifications oldest first, ties broken by number so it is repeatable."""
    return tuple(sorted(modifications, key=lambda m: (m.signed_on, m.number)))


def apply(contract: Contract, modifications: Iterable[Modification]) -> Modified:
    """Work the modifications into the contract they modify."""
    ordered = in_order(modifications)
    items = list(contract.items)
    days = contract.days
    added = 0
    for one in ordered:
        if one.change is Change.TIME:
            days += one.days
            added += one.days
            continue
        found = next((i for i, item in enumerate(items) if item.ident == one.item), None)
        if one.change is Change.ITEM:
            if found is not None:
                raise RuleError(f"{one.number} adds {one.item}, which the contract already has")
            items.append(_added(one))
            continue
        if found is None:
            raise RuleError(f"{one.number} reprices {one.item}, which the contract has not")
        items[found] = _repriced(items[found], one)
    return Modified(
        contract=Contract(
            number=contract.number,
            awarded=contract.awarded,
            notice_to_proceed=contract.notice_to_proceed,
            days=days,
            retainage=contract.retainage,
            liquidated=contract.liquidated,
            items=tuple(items),
        ),
        applied=ordered,
        added_days=added,
    )


def _added(one: Modification) -> LineItem:
    if one.price is None:
        raise RuleError(f"{one.number} adds {one.item} with no price")
    return LineItem(
        ident=one.item,
        description=one.description,
        unit=Unit.LUMP_SUM,
        unit_price=one.price,
    )


def _repriced(item: LineItem, one: Modification) -> LineItem:
    if one.price is None:
        raise RuleError(f"{one.number} reprices {one.item} to nothing")
    return LineItem(
        ident=item.ident,
        description=item.description,
        unit=item.unit,
        unit_price=one.price,
        group=item.group,
        estimated=item.estimated,
    )
