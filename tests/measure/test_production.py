"""Production against effective hours, and cycle time against trips."""

from __future__ import annotations

import datetime as dt

import pytest

from scowbox.errors import FieldError
from scowbox.measure.production import Rate, best, by_day, over, worst
from scowbox.model.scow import ScowTrip
from scowbox.model.shift import Downtime, Reason, Shift
from scowbox.units.clock import moment
from scowbox.units.volume import Yards

DAY = dt.date(2025, 11, 3)
NEXT = dt.date(2025, 11, 4)
LOAD = Yards.of_yards(2240)


def a_shift(ident: str, day: dt.date, begin: str, end: str, *stops: Downtime) -> Shift:
    return Shift(ident, "DR-003", "RCH-012", moment(day, begin), moment(day, end), stops)


def a_trip(ident: str, day: dt.date) -> ScowTrip:
    return ScowTrip(ident, "SC-004", "RCH-012", day, "PA-002")


def test_a_rate_divides_yards_by_effective_hours() -> None:
    rate = Rate(hours=10.0, yards=Yards.of_yards(5000), trips=2)
    assert rate.yards_per_hour == 500.0


def test_a_rate_divides_yards_by_trips() -> None:
    rate = Rate(hours=10.0, yards=Yards.of_yards(5000), trips=2)
    assert rate.yards_per_trip == 2500.0


def test_cycle_time_is_hours_over_trips_in_minutes() -> None:
    rate = Rate(hours=10.0, yards=Yards.of_yards(5000), trips=4)
    assert rate.minutes_per_trip == 150.0


def test_no_hours_worked_is_no_rate() -> None:
    rate = Rate(hours=0.0, yards=Yards.zero(), trips=0)
    assert rate.yards_per_hour is None
    assert rate.minutes_per_trip is None
    assert not rate.worked


def test_no_trips_is_no_load_and_no_cycle() -> None:
    rate = Rate(hours=10.0, yards=Yards.of_yards(5000), trips=0)
    assert rate.yards_per_trip is None
    assert rate.minutes_per_trip is None
    assert rate.yards_per_hour == 500.0


def test_a_rate_refuses_impossible_counts() -> None:
    with pytest.raises(FieldError):
        Rate(hours=-1.0, yards=Yards.zero(), trips=0)
    with pytest.raises(FieldError):
        Rate(hours=1.0, yards=Yards.zero(), trips=-1)


def test_downtime_comes_off_the_hours_a_rate_is_against() -> None:
    stopped = a_shift(
        "SH-00021",
        DAY,
        "06:00",
        "18:00",
        Downtime(moment(DAY, "06:00"), moment(DAY, "12:00"), Reason.WEATHER),
    )
    rate = over([stopped], Yards.of_yards(3000), 2)
    assert rate.hours == 6.0
    assert rate.yards_per_hour == 500.0


def test_a_run_of_shifts_adds_its_hours() -> None:
    rate = over(
        [a_shift("SH-00021", DAY, "06:00", "18:00"), a_shift("SH-00022", NEXT, "06:00", "12:00")],
        Yards.of_yards(9000),
        4,
    )
    assert rate.hours == 18.0
    assert rate.yards_per_hour == 500.0


def test_each_day_gets_its_own_rate() -> None:
    rates = dict(
        by_day(
            [
                a_shift("SH-00021", DAY, "06:00", "18:00"),
                a_shift("SH-00022", NEXT, "06:00", "12:00"),
            ],
            [a_trip("TR-00001", DAY), a_trip("TR-00002", DAY), a_trip("TR-00003", NEXT)],
            LOAD,
        )
    )
    assert rates[DAY].trips == 2
    assert rates[DAY].yards == Yards.of_yards(4480)
    assert rates[NEXT].trips == 1


def test_a_day_with_shifts_and_no_trips_still_appears() -> None:
    rates = dict(by_day([a_shift("SH-00021", DAY, "06:00", "18:00")], [], LOAD))
    assert rates[DAY].trips == 0
    assert rates[DAY].yards == Yards.zero()


def test_a_day_with_trips_and_no_shift_still_appears() -> None:
    rates = dict(by_day([], [a_trip("TR-00001", DAY)], LOAD))
    assert rates[DAY].hours == 0.0
    assert rates[DAY].yards_per_hour is None


def test_the_days_come_back_oldest_first() -> None:
    rates = by_day(
        [a_shift("SH-00022", NEXT, "06:00", "12:00"), a_shift("SH-00021", DAY, "06:00", "18:00")],
        [],
        LOAD,
    )
    assert [day for day, _ in rates] == [DAY, NEXT]


def test_the_best_and_worst_days_are_found() -> None:
    rates = by_day(
        [a_shift("SH-00021", DAY, "06:00", "18:00"), a_shift("SH-00022", NEXT, "06:00", "12:00")],
        [a_trip("TR-00001", DAY), a_trip("TR-00002", NEXT), a_trip("TR-00003", NEXT)],
        LOAD,
    )
    top = best(rates)
    bottom = worst(rates)
    assert top is not None
    assert bottom is not None
    assert top[0] == NEXT
    assert bottom[0] == DAY


def test_a_day_nobody_worked_is_not_the_best_day() -> None:
    rates = by_day([], [a_trip("TR-00001", DAY)], LOAD)
    assert best(rates) is None
    assert worst(rates) is None
