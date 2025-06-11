"""Downtime sorted three ways, and the day credit rule."""

from __future__ import annotations

import datetime as dt

import pytest

from scowbox.errors import FieldError
from scowbox.model.shift import Downtime, Reason, Shift
from scowbox.pay.timeloss import credited_days, extension, standby_days, tally
from scowbox.units.clock import moment

DAY = dt.date(2025, 5, 6)
NEXT = dt.date(2025, 5, 7)


def a_stop(day: dt.date, begin: str, end: str, reason: Reason) -> Downtime:
    return Downtime(moment(day, begin), moment(day, end), reason)


def a_shift(
    ident: str = "SH-00021",
    day: dt.date = DAY,
    begin: str = "06:00",
    end: str = "18:00",
    *stops: Downtime,
) -> Shift:
    return Shift(
        ident=ident,
        dredge="DR-003",
        reach="RCH-012",
        began=moment(day, begin),
        ended=moment(day, end),
        downtimes=stops,
    )


def test_a_clean_run_is_all_effective() -> None:
    got = tally([a_shift()])
    assert got.gross_hours == 12.0
    assert got.effective_hours == 12.0
    assert got.down_hours == 0.0
    assert got.share_effective == 1.0


def test_nothing_at_all_tallies_to_nothing() -> None:
    got = tally([])
    assert got.shifts == 0
    assert got.share_effective == 0.0


def test_allowable_and_contractor_time_split() -> None:
    got = tally(
        [
            a_shift(
                "SH-00021",
                DAY,
                "06:00",
                "18:00",
                a_stop(DAY, "09:00", "11:00", Reason.WEATHER),
                a_stop(DAY, "13:00", "14:00", Reason.BREAKDOWN),
            )
        ]
    )
    assert got.down_hours == 3.0
    assert got.allowable_hours == 2.0
    assert got.contractor_hours == 1.0


def test_standby_is_a_narrower_set_than_allowable() -> None:
    got = tally(
        [
            a_shift(
                "SH-00021",
                DAY,
                "06:00",
                "18:00",
                a_stop(DAY, "09:00", "11:00", Reason.WEATHER),
                a_stop(DAY, "13:00", "14:00", Reason.TRAFFIC),
            )
        ]
    )
    assert got.allowable_hours == 3.0
    assert got.standby_hours == 1.0


def test_hours_come_back_by_reason() -> None:
    got = tally(
        [
            a_shift(
                "SH-00021",
                DAY,
                "06:00",
                "18:00",
                a_stop(DAY, "09:00", "11:00", Reason.WEATHER),
            )
        ]
    )
    assert got.hours_for(Reason.WEATHER) == 2.0
    assert got.hours_for(Reason.CREW) == 0.0


def test_the_same_reason_on_two_shifts_adds_up() -> None:
    got = tally(
        [
            a_shift(
                "SH-00021", DAY, "06:00", "18:00", a_stop(DAY, "09:00", "11:00", Reason.WEATHER)
            ),
            a_shift(
                "SH-00022", NEXT, "06:00", "18:00", a_stop(NEXT, "09:00", "10:00", Reason.WEATHER)
            ),
        ]
    )
    assert got.hours_for(Reason.WEATHER) == 3.0
    assert got.shifts == 2


def test_a_day_rained_off_past_the_share_is_credited() -> None:
    lost = a_shift("SH-00021", DAY, "06:00", "18:00", a_stop(DAY, "06:00", "13:00", Reason.WEATHER))
    assert credited_days([lost]) == (DAY,)
    assert extension([lost]) == 1


def test_a_day_just_under_the_share_is_not_credited() -> None:
    partial = a_shift(
        "SH-00021", DAY, "06:00", "18:00", a_stop(DAY, "06:00", "11:00", Reason.WEATHER)
    )
    assert credited_days([partial]) == ()


def test_exactly_at_the_share_is_credited() -> None:
    half = a_shift("SH-00021", DAY, "06:00", "18:00", a_stop(DAY, "06:00", "12:00", Reason.WEATHER))
    assert credited_days([half]) == (DAY,)


def test_a_short_shift_lost_entirely_is_credited() -> None:
    short = a_shift(
        "SH-00021", DAY, "06:00", "12:00", a_stop(DAY, "06:00", "12:00", Reason.WEATHER)
    )
    assert credited_days([short]) == (DAY,)


def test_contractor_downtime_does_not_credit_a_day() -> None:
    broken = a_shift(
        "SH-00021", DAY, "06:00", "18:00", a_stop(DAY, "06:00", "18:00", Reason.BREAKDOWN)
    )
    assert credited_days([broken]) == ()


def test_two_shifts_on_one_day_are_weighed_together() -> None:
    morning = a_shift(
        "SH-00021", DAY, "06:00", "12:00", a_stop(DAY, "06:00", "12:00", Reason.WEATHER)
    )
    afternoon = a_shift("SH-00022", DAY, "12:00", "20:00")
    assert credited_days([morning, afternoon]) == ()


def test_a_day_with_no_shift_is_not_credited() -> None:
    assert credited_days([]) == ()


def test_a_stricter_share_credits_fewer_days() -> None:
    partial = a_shift(
        "SH-00021", DAY, "06:00", "18:00", a_stop(DAY, "06:00", "13:00", Reason.WEATHER)
    )
    assert credited_days([partial], share=0.5) == (DAY,)
    assert credited_days([partial], share=0.75) == ()


def test_a_share_outside_the_range_is_refused() -> None:
    with pytest.raises(FieldError):
        credited_days([], share=0)
    with pytest.raises(FieldError):
        credited_days([], share=1.5)


def test_standby_is_reported_in_day_rate_days() -> None:
    held = a_shift("SH-00021", DAY, "06:00", "18:00", a_stop(DAY, "06:00", "14:00", Reason.TRAFFIC))
    assert standby_days([held]) == 1.0
    assert standby_days([held], hours_in_day=12) == 0.67


def test_a_standby_day_of_no_hours_is_refused() -> None:
    with pytest.raises(FieldError):
        standby_days([], hours_in_day=0)
