"""Times in the book are aware, and periods run forward."""

from __future__ import annotations

import datetime as dt

import pytest

from scowbox.errors import FieldError
from scowbox.units.clock import SITE_ZONE, aware, hours_between, minutes_between, moment

DAY = dt.date(2025, 3, 14)


def test_moment_reads_a_colon_time() -> None:
    when = moment(DAY, "07:45")
    assert when.hour == 7
    assert when.minute == 45
    assert when.tzinfo == SITE_ZONE


def test_moment_reads_a_four_figure_time() -> None:
    assert moment(DAY, "0745") == moment(DAY, "07:45")


@pytest.mark.parametrize("clock", ["", "7", "25:00", "07:60", "quarter to"])
def test_moment_refuses_anything_else(clock: str) -> None:
    with pytest.raises(FieldError):
        moment(DAY, clock)


def test_aware_passes_a_zoned_time_through() -> None:
    when = moment(DAY, "07:45")
    assert aware(when) is when


def test_aware_refuses_a_naive_time() -> None:
    with pytest.raises(FieldError):
        aware(dt.datetime(2025, 3, 14, 7, 45))  # noqa: DTZ001


def test_minutes_between_counts_whole_minutes() -> None:
    assert minutes_between(moment(DAY, "07:45"), moment(DAY, "09:15")) == 90


def test_minutes_between_refuses_a_period_that_runs_backwards() -> None:
    with pytest.raises(FieldError):
        minutes_between(moment(DAY, "09:15"), moment(DAY, "07:45"))


def test_hours_between_reports_to_the_hundredth() -> None:
    assert hours_between(moment(DAY, "07:45"), moment(DAY, "09:15")) == 1.5
    assert hours_between(moment(DAY, "07:00"), moment(DAY, "07:20")) == 0.33
