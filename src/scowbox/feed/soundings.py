"""Sounding exports.

The survey software writes one row per shot with a header line:

    station,offset,depth,time
    100+00,-50.0,41.2,07:45
    100+00,0.0,43.8,07:45

Station is surveyor notation, offset is feet from the centreline positive to
the right, depth is the raw reading in feet and time is the shot's clock on the
project's own zone. The day comes from the survey the file is being loaded
into, not from the file, because the export does not carry one.
"""

from __future__ import annotations

import csv
import datetime as dt
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from scowbox.errors import FieldError
from scowbox.model.survey import Sounding
from scowbox.units.clock import moment
from scowbox.units.depth import Depth
from scowbox.units.station import Station

HEADINGS = ("station", "offset", "depth", "time")


@dataclass(frozen=True)
class Reading:
    """What one line of the file turned into, or why it did not."""

    line: int
    sounding: Sounding | None
    trouble: str | None

    @property
    def read(self) -> bool:
        return self.sounding is not None


def parse_lines(lines: Iterable[str], day: dt.date) -> tuple[Reading, ...]:
    """Read an export into soundings, one result per line, in file order."""
    rows = csv.reader(lines)
    try:
        heading = next(rows)
    except StopIteration:
        raise FieldError("file", "the export is empty") from None
    got = tuple(h.strip().lower() for h in heading)
    if got != HEADINGS:
        raise FieldError("file", f"heading is {','.join(got)}, expected {','.join(HEADINGS)}")
    out = []
    for number, row in enumerate(rows, start=2):
        if not row:
            continue
        out.append(_read_row(number, row, day))
    return tuple(out)


def _read_row(number: int, row: list[str], day: dt.date) -> Reading:
    if len(row) != len(HEADINGS):
        return Reading(number, None, f"{len(row)} fields, expected {len(HEADINGS)}")
    station, offset, depth, clock = (field.strip() for field in row)
    try:
        sounding = Sounding(
            station=Station.parse(station),
            offset=float(offset),
            raw_depth=Depth.of_feet(float(depth)),
            taken=moment(day, clock),
        )
    except FieldError as error:
        return Reading(number, None, error.message)
    except ValueError:
        return Reading(number, None, f"{offset!r} and {depth!r} are not both numbers")
    return Reading(number, sounding, None)


def parse_file(path: str | Path, day: dt.date) -> tuple[Reading, ...]:
    """Read an export off disk."""
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return parse_lines(handle, day)


def kept(readings: Iterable[Reading]) -> tuple[Sounding, ...]:
    """Just the soundings, for handing to the store."""
    return tuple(r.sounding for r in readings if r.sounding is not None)


def refused(readings: Iterable[Reading]) -> tuple[Reading, ...]:
    """Just the lines that did not read, still carrying their line numbers."""
    return tuple(r for r in readings if r.sounding is None)
