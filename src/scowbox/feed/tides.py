"""Gauge downloads.

The water level service writes a wide file and only three of its columns matter
here:

    Date Time,Water Level,Sigma,O,F,R,L,Quality
    2025-03-14 07:00,1.023,0.010,0,0,0,0,v

``Date Time`` is on the gauge's own standard time, which is the project's zone.
``Water Level`` is feet above datum. ``Quality`` is ``v`` for verified and ``p``
for preliminary, and the difference is worth keeping: a quantity computed
against preliminary water levels can move when the month is verified, so the
count of preliminary readings comes back with the parse rather than being
noticed later.

The ``F`` column is the flat tolerance flag. A reading carrying it is one the
service itself does not stand behind, and it is left out.
"""

from __future__ import annotations

import csv
import datetime as dt
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from scowbox.datum.tide import TideReading
from scowbox.errors import FieldError
from scowbox.units.clock import SITE_ZONE

TIME_COLUMN = "date time"
LEVEL_COLUMN = "water level"
QUALITY_COLUMN = "quality"
FLAT_COLUMN = "f"
VERIFIED = "v"

SITE_OFFSET = dt.datetime(2000, 1, 1, tzinfo=SITE_ZONE).strftime("%z")
"""The gauge publishes on standard time and never shifts, so the offset can be
stapled on before parsing rather than after. Taken off the project zone so that
moving the project does not leave a literal here disagreeing with it."""


@dataclass(frozen=True)
class Download:
    """A parsed gauge file."""

    gauge: str
    readings: tuple[TideReading, ...]
    preliminary: int
    flagged: int
    refused: tuple[int, ...]

    @property
    def count(self) -> int:
        return len(self.readings)

    @property
    def all_verified(self) -> bool:
        return self.preliminary == 0


def parse_lines(lines: Iterable[str], gauge: str) -> Download:
    """Read a download into readings, counting what was left out and why."""
    rows = csv.reader(lines)
    try:
        heading = [h.strip().lower() for h in next(rows)]
    except StopIteration:
        raise FieldError("file", "the download is empty") from None
    for wanted in (TIME_COLUMN, LEVEL_COLUMN):
        if wanted not in heading:
            raise FieldError("file", f"the download has no {wanted!r} column")
    where = {name: index for index, name in enumerate(heading)}
    readings: list[TideReading] = []
    preliminary = 0
    flagged = 0
    refused: list[int] = []
    for number, row in enumerate(rows, start=2):
        if not row:
            continue
        outcome = _read_row(row, where)
        if outcome is None:
            refused.append(number)
            continue
        reading, quality, flat = outcome
        if flat:
            flagged += 1
            continue
        if quality != VERIFIED:
            preliminary += 1
        readings.append(reading)
    return Download(gauge, tuple(readings), preliminary, flagged, tuple(refused))


def _read_row(row: list[str], where: dict[str, int]) -> tuple[TideReading, str, bool] | None:
    def field(name: str, fallback: str = "") -> str:
        index = where.get(name)
        if index is None or index >= len(row):
            return fallback
        return row[index].strip()

    try:
        when = dt.datetime.strptime(f"{field(TIME_COLUMN)} {SITE_OFFSET}", "%Y-%m-%d %H:%M %z")
        reading = TideReading(when, float(field(LEVEL_COLUMN)))
    except (ValueError, FieldError):
        return None
    flat = field(FLAT_COLUMN, "0") not in ("", "0")
    return reading, field(QUALITY_COLUMN, VERIFIED).lower(), flat


def parse_file(path: str | Path, gauge: str) -> Download:
    """Read a download off disk."""
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return parse_lines(handle, gauge)
