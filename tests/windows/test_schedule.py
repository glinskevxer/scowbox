"""Windows, and what governs where they overlap."""

from __future__ import annotations

import datetime as dt

import pytest

from scowbox.errors import FieldError
from scowbox.model.window import Restriction, Window
from scowbox.windows.schedule import Schedule


def a_window(
    name: str = "loggerhead",
    begins: dt.date = dt.date(2025, 5, 1),
    ends: dt.date = dt.date(2025, 11, 30),
    restriction: Restriction = Restriction.CLOSED,
    reach: str = "",
) -> Window:
    return Window(name, begins, ends, restriction, "NMFS", reach)


def test_strictness_ranks_in_the_order_the_words_do() -> None:
    assert Restriction.CLOSED.rank > Restriction.OBSERVER.rank > Restriction.OPEN.rank
    assert Restriction.CLOSED.stops_work
    assert not Restriction.OBSERVER.stops_work


def test_a_window_covers_both_of_its_ends() -> None:
    window = a_window()
    assert window.covers(dt.date(2025, 5, 1))
    assert window.covers(dt.date(2025, 11, 30))
    assert not window.covers(dt.date(2025, 4, 30))


def test_a_window_counts_its_days_inclusively() -> None:
    assert a_window(begins=dt.date(2025, 5, 1), ends=dt.date(2025, 5, 1)).days == 1
    assert a_window(begins=dt.date(2025, 5, 1), ends=dt.date(2025, 5, 3)).days == 3


def test_a_window_with_no_reach_binds_the_whole_job() -> None:
    window = a_window()
    assert window.whole_job
    assert window.applies_to("RCH-012")
    assert window.applies_to("RCH-999")


def test_a_window_on_one_reach_binds_only_it() -> None:
    window = a_window(reach="RCH-012")
    assert not window.whole_job
    assert window.applies_to("RCH-012")
    assert not window.applies_to("RCH-014")


def test_a_window_that_ends_first_is_refused() -> None:
    with pytest.raises(FieldError):
        a_window(begins=dt.date(2025, 11, 30), ends=dt.date(2025, 5, 1))


def test_a_window_needs_a_name_and_an_authority() -> None:
    with pytest.raises(FieldError):
        Window(" ", dt.date(2025, 5, 1), dt.date(2025, 6, 1), Restriction.CLOSED, "NMFS")
    with pytest.raises(FieldError):
        Window("turtle", dt.date(2025, 5, 1), dt.date(2025, 6, 1), Restriction.CLOSED, "")


def test_a_window_on_something_that_is_not_a_reach_is_refused() -> None:
    with pytest.raises(FieldError):
        a_window(reach="SC-004")


def test_a_window_describes_itself() -> None:
    text = a_window(reach="RCH-012").describe()
    assert text == "loggerhead (NMFS): 2025-05-01 to 2025-11-30, RCH-012, closed"
    assert "all reaches" in a_window().describe()


def test_nothing_in_force_is_open() -> None:
    empty = Schedule.of([])
    assert empty.on(dt.date(2025, 7, 1), "RCH-012") is Restriction.OPEN
    assert not empty.closed(dt.date(2025, 7, 1), "RCH-012")


def test_one_window_governs_on_its_own() -> None:
    schedule = Schedule.of([a_window()])
    assert schedule.on(dt.date(2025, 7, 1), "RCH-012") is Restriction.CLOSED


def test_the_stricter_of_two_overlapping_windows_governs() -> None:
    schedule = Schedule.of(
        [
            a_window("oyster", restriction=Restriction.OBSERVER),
            a_window("loggerhead", restriction=Restriction.CLOSED),
        ]
    )
    assert schedule.on(dt.date(2025, 7, 1), "RCH-012") is Restriction.CLOSED


def test_the_answer_does_not_depend_on_the_order_they_arrived() -> None:
    strict = a_window("loggerhead", restriction=Restriction.CLOSED)
    loose = a_window("oyster", restriction=Restriction.OBSERVER)
    assert Schedule.of([strict, loose]).on(dt.date(2025, 7, 1), "RCH-012") is Schedule.of(
        [loose, strict]
    ).on(dt.date(2025, 7, 1), "RCH-012")


def test_windows_in_force_come_back_strictest_first() -> None:
    schedule = Schedule.of(
        [
            a_window("oyster", restriction=Restriction.OBSERVER),
            a_window("loggerhead", restriction=Restriction.CLOSED),
        ]
    )
    found = schedule.in_force(dt.date(2025, 7, 1), "RCH-012")
    assert [w.name for w in found] == ["loggerhead", "oyster"]


def test_a_window_on_another_reach_does_not_bind() -> None:
    schedule = Schedule.of([a_window(reach="RCH-014")])
    assert schedule.on(dt.date(2025, 7, 1), "RCH-012") is Restriction.OPEN
    assert schedule.on(dt.date(2025, 7, 1), "RCH-014") is Restriction.CLOSED


def test_the_closed_days_of_a_period_can_be_listed() -> None:
    schedule = Schedule.of([a_window(begins=dt.date(2025, 5, 1), ends=dt.date(2025, 5, 3))])
    closed = schedule.days_between(
        dt.date(2025, 4, 29), dt.date(2025, 5, 5), "RCH-012", Restriction.CLOSED
    )
    assert closed == (dt.date(2025, 5, 1), dt.date(2025, 5, 2), dt.date(2025, 5, 3))


def test_a_period_that_runs_backwards_is_refused() -> None:
    with pytest.raises(FieldError):
        Schedule.of([]).days_between(
            dt.date(2025, 5, 5), dt.date(2025, 5, 1), "RCH-012", Restriction.OPEN
        )


def test_the_next_open_day_is_the_day_after_a_closure() -> None:
    schedule = Schedule.of([a_window(begins=dt.date(2025, 5, 1), ends=dt.date(2025, 5, 3))])
    assert schedule.next_open(dt.date(2025, 5, 1), "RCH-012") == dt.date(2025, 5, 4)


def test_an_open_day_is_its_own_next_open_day() -> None:
    schedule = Schedule.of([a_window(begins=dt.date(2025, 5, 1), ends=dt.date(2025, 5, 3))])
    assert schedule.next_open(dt.date(2025, 4, 28), "RCH-012") == dt.date(2025, 4, 28)


def test_a_closure_longer_than_the_search_finds_nothing() -> None:
    schedule = Schedule.of([a_window(begins=dt.date(2025, 5, 1), ends=dt.date(2030, 5, 3))])
    assert schedule.next_open(dt.date(2025, 5, 1), "RCH-012") is None


def test_the_windows_of_a_reach_come_back_in_date_order() -> None:
    schedule = Schedule.of(
        [
            a_window("sturgeon", dt.date(2025, 2, 1), dt.date(2025, 4, 30)),
            a_window("loggerhead"),
            a_window("shortnose", reach="RCH-014"),
        ]
    )
    assert [w.name for w in schedule.for_reach("RCH-012")] == ["sturgeon", "loggerhead"]
