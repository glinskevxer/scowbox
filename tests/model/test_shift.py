"""Shift logs, their interruptions, and the two things a reason decides."""

from __future__ import annotations

import datetime as dt

import pytest

from scowbox.errors import FieldError
from scowbox.model.plant import Dredge, Plant
from scowbox.model.shift import Downtime, Reason, Shift
from scowbox.units.clock import moment

DAY = dt.date(2025, 5, 6)


def a_stop(begin: str, end: str, reason: Reason = Reason.WEATHER) -> Downtime:
    return Downtime(moment(DAY, begin), moment(DAY, end), reason)


def a_shift(*stops: Downtime, **over: object) -> Shift:
    fields: dict[str, object] = {
        "ident": "SH-00021",
        "dredge": "DR-003",
        "reach": "RCH-012",
        "began": moment(DAY, "06:00"),
        "ended": moment(DAY, "18:00"),
        "downtimes": stops,
    }
    fields.update(over)
    return Shift(**fields)  # type: ignore[arg-type]


def test_only_three_reasons_are_allowable() -> None:
    allowed = {r for r in Reason if r.allowable}
    assert allowed == {Reason.WEATHER, Reason.TRAFFIC, Reason.ENVIRONMENTAL}


def test_only_two_reasons_are_paid_standby() -> None:
    paid = {r for r in Reason if r.standby}
    assert paid == {Reason.TRAFFIC, Reason.ENVIRONMENTAL}


def test_weather_buys_time_but_not_money() -> None:
    assert Reason.WEATHER.allowable
    assert not Reason.WEATHER.standby


def test_a_breakdown_buys_neither() -> None:
    assert not Reason.BREAKDOWN.allowable
    assert not Reason.BREAKDOWN.standby


def test_an_interruption_knows_its_length() -> None:
    stop = a_stop("09:00", "10:30")
    assert stop.minutes == 90
    assert stop.hours == 1.5


def test_an_interruption_that_ends_first_is_refused() -> None:
    with pytest.raises(FieldError):
        a_stop("10:30", "09:00")


def test_a_clean_shift_is_all_effective() -> None:
    shift = a_shift()
    assert shift.gross_hours == 12.0
    assert shift.effective_hours == 12.0
    assert shift.down_minutes == 0


def test_interruptions_come_off_the_effective_hours() -> None:
    shift = a_shift(a_stop("09:00", "10:30"), a_stop("14:00", "14:30"))
    assert shift.down_minutes == 120
    assert shift.effective_hours == 10.0


def test_minutes_can_be_asked_for_by_reason() -> None:
    shift = a_shift(
        a_stop("09:00", "10:30", Reason.WEATHER),
        a_stop("14:00", "14:30", Reason.BREAKDOWN),
    )
    assert shift.stopped_for(Reason.WEATHER) == 90
    assert shift.stopped_for(Reason.BREAKDOWN) == 30
    assert shift.stopped_for(Reason.CREW) == 0


def test_the_shift_is_logged_against_the_day_it_started() -> None:
    assert a_shift().day == DAY


def test_a_shift_that_ends_before_it_begins_is_refused() -> None:
    with pytest.raises(FieldError):
        a_shift(ended=moment(DAY, "05:00"))


def test_an_interruption_outside_the_shift_is_refused() -> None:
    with pytest.raises(FieldError, match="outside"):
        a_shift(a_stop("05:00", "05:30"))
    with pytest.raises(FieldError, match="outside"):
        a_shift(a_stop("17:30", "19:00"))


def test_two_interruptions_that_overlap_are_refused() -> None:
    with pytest.raises(FieldError, match="overlap"):
        a_shift(a_stop("09:00", "11:00"), a_stop("10:00", "12:00"))


def test_interruptions_that_touch_are_allowed() -> None:
    shift = a_shift(a_stop("09:00", "11:00"), a_stop("11:00", "12:00"))
    assert shift.down_minutes == 180


@pytest.mark.parametrize(
    ("field_name", "value"),
    [("ident", "DR-003"), ("dredge", "SH-00021"), ("reach", "DR-003")],
)
def test_a_shift_checks_every_identifier(field_name: str, value: str) -> None:
    with pytest.raises(FieldError) as caught:
        a_shift(**{field_name: value})
    assert caught.value.field == field_name


def test_a_mechanical_dredge_loads_scows() -> None:
    assert Plant.MECHANICAL.loads_scows
    assert not Plant.CUTTER.loads_scows
    assert Plant.CUTTER.moves_pipeline


def test_a_dredge_describes_itself() -> None:
    dredge = Dredge("DR-003", "Cherokee", Plant.MECHANICAL, "Norfolk Dredging")
    assert dredge.describe() == "DR-003 Cherokee, mechanical, Norfolk Dredging"


def test_a_dredge_needs_an_identifier_a_name_and_an_operator() -> None:
    with pytest.raises(FieldError):
        Dredge("SH-00021", "Cherokee", Plant.MECHANICAL, "Norfolk Dredging")
    with pytest.raises(FieldError):
        Dredge("DR-003", " ", Plant.MECHANICAL, "Norfolk Dredging")
    with pytest.raises(FieldError):
        Dredge("DR-003", "Cherokee", Plant.MECHANICAL, "")
