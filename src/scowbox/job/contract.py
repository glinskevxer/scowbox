"""The contract as the estimates should see it.

Nothing above this reads the contract straight out of the book. The version
that matters is the one with every signed modification worked into it, and a
report that priced a quantity at the original schedule while a modification
repriced it six months ago is a report that disagrees with the cheque.
"""

from __future__ import annotations

import sqlite3

from scowbox.model.contract import Contract
from scowbox.pay.modified import Modified, apply
from scowbox.store import contracts, modifications


def as_modified(connection: sqlite3.Connection, number: str | None = None) -> Modified:
    """The contract with its modifications applied, in signature order."""
    held = contracts.get(connection, number) if number else contracts.only(connection)
    return apply(held, modifications.listed(connection, held.number))


def current(connection: sqlite3.Connection, number: str | None = None) -> Contract:
    """The contract as modified, for callers that only want the schedule."""
    return as_modified(connection, number).contract
