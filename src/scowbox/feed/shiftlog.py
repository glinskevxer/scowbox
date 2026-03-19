"""The tender's shift log, as it comes off the boat.

Two files, because that is how they arrive. The shift file has one row a shift:

    shift,dredge,reach,day,from,to
    SH-00021,DR-003,RCH-012,2026-03-10,06:00,18:00

The stop file has one row an interruption, against the shift it belongs to:

    shift,from,to,reason,note
    SH-00021,09:00,11:00,weather,squall through

The day comes off the shift, never off the stop row, because the tender does
not write it there and a stop typed with today's date on it lands outside the
shift it belongs to and is refused for a reason that makes no sense to anybody.
"""

from __future__ import annotations

import csv
import datetime as dt
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from scowbox.errors import FieldError
from scowbox.model.shift import Downtime, Reason, Shift
from scowbox.units.clock import moment

SHIFT_HEADINGS = ("shift", "dredge", "reach", "day", "from", "to")
STOP_HEADINGS = ("shift", "from", "to", "reason", "note")


@dataclass(frozen=True)
class Read:
    """What one line turned into, or why it did not."""

    line: int
    shift: Shift | None = None
    stop: tuple[str, Downtime] | None = None
    trouble: str | None = None

    @property
    def read(self) -> bool:
        return self.trouble is None


def _rows(lines: Iterable[str], headings: tuple[str, ...]) -> list[list[str]]:
    reader = csv.reader(lines)
    try:
        got = tuple(h.strip().lower() for h in next(reader))
    except StopIteration:
        raise FieldError("file", "the log is empty") from None
    if got != headings:
        raise FieldError("file", f"heading is {','.join(got)}, expected {','.join(headings)}")
    return [row for row in reader if row]


def parse_shifts(lines: Iterable[str]) -> tuple[Read, ...]:
    """Read the shift file, one result a line, in file order."""
    out = []
    for number, row in enumerate(_rows(lines, SHIFT_HEADINGS), start=2):
        out.append(_shift(number, row))
    return tuple(out)


def _shift(number: int, row: list[str]) -> Read:
    if len(row) != len(SHIFT_HEADINGS):
        return Read(number, trouble=f"{len(row)} fields, expected {len(SHIFT_HEADINGS)}")
    ident, dredge, reach, day, began, ended = (field.strip() for field in row)
    try:
        worked = dt.date.fromisoformat(day)
        return Read(
            number,
            shift=Shift(
                ident=ident,
                dredge=dredge,
                reach=reach,
                began=moment(worked, began),
                ended=moment(worked, ended),
            ),
        )
    except FieldError as error:
        return Read(number, trouble=error.message)
    except ValueError:
        return Read(number, trouble=f"{day!r} is not a day such as 2026-03-10")


def parse_stops(lines: Iterable[str], days: dict[str, dt.date]) -> tuple[Read, ...]:
    """Read the stop file against the days its shifts were worked."""
    out = []
    for number, row in enumerate(_rows(lines, STOP_HEADINGS), start=2):
        out.append(_stop(number, row, days))
    return tuple(out)


def _stop(number: int, row: list[str], days: dict[str, dt.date]) -> Read:
    if len(row) != len(STOP_HEADINGS):
        return Read(number, trouble=f"{len(row)} fields, expected {len(STOP_HEADINGS)}")
    ident, began, ended, reason, note = (field.strip() for field in row)
    day = days.get(ident)
    if day is None:
        return Read(number, trouble=f"{ident} is not a shift in this log")
    try:
        why = Reason(reason)
    except ValueError:
        return Read(number, trouble=f"{reason!r} is not a reason work stops")
    try:
        return Read(
            number,
            stop=(ident, Downtime(moment(day, began), moment(day, ended), why, note)),
        )
    except FieldError as error:
        return Read(number, trouble=error.message)


def parse_files(
    shifts: str | Path, stops: str | Path | None = None
) -> tuple[tuple[Read, ...], tuple[Read, ...]]:
    """Read both files off disk, the stops against the shifts."""
    with Path(shifts).open(newline="", encoding="utf-8") as handle:
        worked = parse_shifts(handle)
    if stops is None:
        return worked, ()
    days = {r.shift.ident: r.shift.day for r in worked if r.shift is not None}
    with Path(stops).open(newline="", encoding="utf-8") as handle:
        return worked, parse_stops(handle, days)


def kept_shifts(reads: Iterable[Read]) -> tuple[Shift, ...]:
    """Just the shifts, for handing to the store."""
    return tuple(r.shift for r in reads if r.shift is not None)


def kept_stops(reads: Iterable[Read]) -> tuple[tuple[str, Downtime], ...]:
    """Just the interruptions, each with the shift it belongs to."""
    return tuple(r.stop for r in reads if r.stop is not None)


def refused(reads: Iterable[Read]) -> tuple[Read, ...]:
    """Just the lines that would not read, still carrying their line numbers."""
    return tuple(r for r in reads if not r.read)
