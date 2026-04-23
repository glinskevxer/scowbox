"""Scow trip sheets, as the inspector writes them.

One row a trip, with the box measure on the same row:

    trip,scow,reach,day,placement,light,pb,sb,ps,ss
    TR-00001,SC-004,RCH-012,2026-05-04,PA-002,12.0,4.0,4.0,4.0,4.0

The five reading columns are optional, and they are all optional together. A
trip logged before it was measured leaves them blank; a row with three of them
filled in is refused rather than measured on three corners, because a box
measure on three corners is not a box measure and the row that produced it is a
row somebody was interrupted in the middle of.
"""

from __future__ import annotations

import csv
import datetime as dt
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from scowbox.errors import FieldError
from scowbox.model.scow import BoxReading, Corner, ScowTrip

HEADINGS = ("trip", "scow", "reach", "day", "placement", "light", "pb", "sb", "ps", "ss")
CORNERS = (
    ("pb", Corner.PORT_BOW),
    ("sb", Corner.STARBOARD_BOW),
    ("ps", Corner.PORT_STERN),
    ("ss", Corner.STARBOARD_STERN),
)


@dataclass(frozen=True)
class Read:
    """What one row turned into, or why it did not."""

    line: int
    trip: ScowTrip | None
    trouble: str | None

    @property
    def read(self) -> bool:
        return self.trip is not None


def parse_lines(lines: Iterable[str]) -> tuple[Read, ...]:
    """Read a trip sheet, one result a row, in file order."""
    reader = csv.reader(lines)
    try:
        got = tuple(h.strip().lower() for h in next(reader))
    except StopIteration:
        raise FieldError("file", "the sheet is empty") from None
    if got != HEADINGS:
        raise FieldError("file", f"heading is {','.join(got)}, expected {','.join(HEADINGS)}")
    return tuple(_row(number, row) for number, row in enumerate(reader, start=2) if row)


def _row(number: int, row: list[str]) -> Read:
    if len(row) != len(HEADINGS):
        return Read(number, None, f"{len(row)} fields, expected {len(HEADINGS)}")
    fields = dict(zip(HEADINGS, (field.strip() for field in row), strict=True))
    box = [fields["light"], *(fields[key] for key, _ in CORNERS)]
    if any(box) and not all(box):
        return Read(number, None, "a box measure is all five readings or none of them")
    try:
        day = dt.date.fromisoformat(fields["day"])
    except ValueError:
        return Read(number, None, f"{fields['day']!r} is not a day such as 2026-05-04")
    try:
        readings = _readings(fields) if all(box) else ()
        return Read(
            number,
            ScowTrip(
                ident=fields["trip"],
                scow=fields["scow"],
                reach=fields["reach"],
                loaded_on=day,
                placement=fields["placement"],
                readings=readings,
            ),
            None,
        )
    except FieldError as error:
        return Read(number, None, error.message)
    except ValueError:
        return Read(number, None, "a box reading is a number of feet")


def _readings(fields: dict[str, str]) -> tuple[BoxReading, ...]:
    light = float(fields["light"])
    return tuple(BoxReading(corner, light, float(fields[key])) for key, corner in CORNERS)


def parse_file(path: str | Path) -> tuple[Read, ...]:
    """Read a trip sheet off disk."""
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return parse_lines(handle)


def kept(reads: Iterable[Read]) -> tuple[ScowTrip, ...]:
    """Just the trips, for handing to the store."""
    return tuple(r.trip for r in reads if r.trip is not None)


def refused(reads: Iterable[Read]) -> tuple[Read, ...]:
    """Just the rows that would not read, still carrying their line numbers."""
    return tuple(r for r in reads if not r.read)
