"""Times, all of them on the project's own clock.

A sounding is reduced by the tide at the moment it was taken, and the tide
gauge publishes on local standard time. Everything in the book is therefore an
aware datetime in the project's zone. Nothing here asks the machine what time
it is: the operating date arrives as an argument, always.
"""

from __future__ import annotations

import datetime as dt
import re

from scowbox.errors import FieldError

SITE_ZONE = dt.timezone(dt.timedelta(hours=-5), "EST")
"""Eastern standard time, held fixed. The gauge does not shift for daylight
saving and neither does the dredge log, so neither does this."""

_CLOCK = re.compile(r"^([0-9]{1,2}):?([0-9]{2})$")


def moment(day: dt.date, clock: str) -> dt.datetime:
    """Combine a date and a ``HH:MM`` or ``HHMM`` reading into an aware time."""
    match = _CLOCK.match(clock.strip())
    if match is None:
        raise FieldError("time", f"{clock!r} is not a time of day such as 07:45")
    hour, minute = int(match.group(1)), int(match.group(2))
    if hour > 23 or minute > 59:
        raise FieldError("time", f"{clock!r} is not a time of day such as 07:45")
    return dt.datetime(day.year, day.month, day.day, hour, minute, tzinfo=SITE_ZONE)


def aware(when: dt.datetime) -> dt.datetime:
    """Refuse a naive datetime rather than guess which zone it meant."""
    if when.tzinfo is None:
        raise FieldError("time", "a time in the book carries its zone")
    return when


def minutes_between(start: dt.datetime, end: dt.datetime) -> int:
    """Whole minutes from ``start`` to ``end``, which must run forward."""
    if end < start:
        raise FieldError("time", "the end of a period comes after its start")
    return int((end - start).total_seconds() // 60)


def hours_between(start: dt.datetime, end: dt.datetime) -> float:
    """The same period in hours, to the hundredth, as a shift log reports it."""
    return round(minutes_between(start, end) / 60, 2)
