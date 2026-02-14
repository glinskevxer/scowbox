"""Finding whatever a number turns out to be.

Somebody reads an identifier off a ticket, a shift log or an email and wants to
know what it is. The prefix already says which family it belongs to, so the
lookup does not have to guess: it resolves the family, fetches the record and
describes it.

A gauge number and a contract number have no prefix, so those are tried last
and by exact match. Nothing here searches by substring: a program that answers
a partial identifier with three possibilities has made the reader's problem
worse.
"""

from __future__ import annotations

import sqlite3

from scowbox.errors import MissingError
from scowbox.ids import kind_of
from scowbox.store import (
    contracts,
    estimates,
    placements,
    reaches,
    scows,
    shifts,
    surveys,
    tides,
    trips,
)


def _reach(connection: sqlite3.Connection, ident: str) -> list[str]:
    reach = reaches.get(connection, ident)
    return [
        reach.describe(),
        f"  measured by {reach.method.value}, pay group {reach.group}",
        f"  {len(surveys.for_reach(connection, ident)):,} surveys,"
        f" {len(trips.for_reach(connection, ident)):,} trips,"
        f" {len(shifts.for_reach(connection, ident)):,} shifts",
    ]


def _survey(connection: sqlite3.Connection, ident: str) -> list[str]:
    survey = surveys.full(connection, ident)
    return [
        f"{survey.ident} {survey.kind.value} survey of {survey.reach}",
        f"  run {survey.taken_on} by {survey.vessel}, {survey.count:,} shots",
        f"  gauge {survey.gauge or 'none named'}",
    ]


def _scow(connection: sqlite3.Connection, ident: str) -> list[str]:
    scow = scows.get(connection, ident)
    hauled = [t for t in trips.listed(connection) if t.scow == ident]
    return [scow.describe(), f"  {len(hauled):,} trips"]


def _trip(connection: sqlite3.Connection, ident: str) -> list[str]:
    trip = trips.get(connection, ident)
    lines = [
        f"{trip.ident} {trip.scow} out of {trip.reach} on {trip.loaded_on}",
        f"  {'measured' if trip.measured else 'not measured'}, bound for {trip.placement}",
    ]
    try:
        ticket = trips.ticket_of(connection, ident)
    except MissingError:
        lines.append("  no placement ticket")
    else:
        lines.append(f"  released at {ticket.area} on {ticket.released:%Y-%m-%d %H:%M}")
    return lines


def _placement(connection: sqlite3.Connection, ident: str) -> list[str]:
    area = placements.get(connection, ident)
    held = trips.tickets_for_area(connection, ident)
    return [
        f"{area.ident} {area.name}, {area.ground.value}",
        f"  permit {area.permit}, {len(held):,} loads",
    ]


def _plant(connection: sqlite3.Connection, ident: str) -> list[str]:
    dredge = shifts.dredge(connection, ident)
    worked = [s for s in shifts.listed(connection) if s.dredge == ident]
    return [dredge.describe(), f"  {len(worked):,} shifts"]


def _shift(connection: sqlite3.Connection, ident: str) -> list[str]:
    shift = shifts.get(connection, ident)
    return [
        f"{shift.ident} {shift.dredge} on {shift.reach}, {shift.day}",
        f"  {shift.gross_hours:.2f} gross, {shift.effective_hours:.2f} effective",
    ]


def _estimate(connection: sqlite3.Connection, ident: str) -> list[str]:
    one = estimates.get(connection, ident)
    return [
        f"{one.ident} estimate {one.number} through {one.through}",
        f"  earned {one.earned}, retained {one.retained}, due {one.due}",
    ]


FAMILIES = {
    "reach": _reach,
    "survey": _survey,
    "scow": _scow,
    "trip": _trip,
    "placement": _placement,
    "plant": _plant,
    "shift": _shift,
    "estimate": _estimate,
}


def find(connection: sqlite3.Connection, text: str) -> list[str]:
    """Describe whatever the text names, or say what was looked for."""
    wanted = text.strip()
    try:
        family = kind_of(wanted).name
    except Exception:  # noqa: BLE001
        return _unprefixed(connection, wanted)
    reader = FAMILIES.get(family)
    if reader is None:
        return [f"{wanted} is a {family} identifier and nothing here reads those"]
    return reader(connection, wanted)


def _unprefixed(connection: sqlite3.Connection, wanted: str) -> list[str]:
    if wanted in contracts.numbers(connection):
        contract = contracts.get(connection, wanted)
        return [
            f"{contract.number}, awarded {contract.awarded}",
            f"  {contract.days} days, complete {contract.completion},"
            f" {len(contract.items)} line items",
        ]
    if wanted in tides.gauges(connection):
        first, last = tides.span(connection, wanted)
        return [f"gauge {wanted}", f"  readings from {first:%Y-%m-%d} to {last:%Y-%m-%d}"]
    raise MissingError("anything called", wanted)
