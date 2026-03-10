"""How long a confined disposal facility has left."""

from __future__ import annotations

import datetime as dt

import pytest

from scowbox.errors import FieldError
from scowbox.measure.forecast import forecast
from scowbox.model.placement import Grade, Ground, PlacementArea, PlacementTicket
from scowbox.units.clock import moment
from scowbox.units.volume import Yards

FIRST = dt.date(2026, 1, 5)
CELL = PlacementArea(
    "PA-004", "Eagle Island cell 3", Ground.UPLAND, "SAW-2019-01143", Yards.of_yards(100000)
)
OCEAN = PlacementArea("PA-002", "Wilmington ODMDS", Ground.OCEAN, "SAW-2019-01142")


def a_ticket(number: int, day: dt.date, yards: float = 2000, area: str = "PA-004"):  # type: ignore[no-untyped-def]
    return PlacementTicket(
        f"TR-{number:05d}", area, moment(day, "11:20"), Yards.of_yards(yards), Grade.SUITABLE
    )


def some(days: int, a_day: int = 5) -> list[PlacementTicket]:
    return [
        a_ticket(day * a_day + load, FIRST + dt.timedelta(days=day))
        for day in range(days)
        for load in range(a_day)
    ]


def test_nothing_placed_is_nothing_forecast() -> None:
    got = forecast(CELL, [], FIRST)
    assert got.loads == 0
    assert got.placed == Yards.zero()
    assert got.a_day is None
    assert got.average_load is None


def test_the_loads_and_the_days_are_counted() -> None:
    got = forecast(CELL, some(4), FIRST + dt.timedelta(days=3))
    assert got.loads == 20
    assert got.days == 4


def test_the_placed_volume_adds_the_tickets_up() -> None:
    got = forecast(CELL, some(4), FIRST + dt.timedelta(days=3))
    assert got.placed == Yards.of_yards(40000)
    assert got.remaining == Yards.of_yards(60000)


def test_the_rate_is_over_the_days_the_tickets_cover() -> None:
    got = forecast(CELL, some(4), FIRST + dt.timedelta(days=3))
    assert got.a_day == 10000.0


def test_one_day_of_tickets_is_not_a_rate() -> None:
    got = forecast(CELL, some(1), FIRST)
    assert got.days == 1
    assert got.a_day is None
    assert got.days_left is None
    assert got.full_on is None


def test_the_average_load_is_over_the_tickets() -> None:
    got = forecast(CELL, some(4), FIRST + dt.timedelta(days=3))
    assert got.average_load == Yards.of_yards(2000)


def test_the_loads_left_are_the_room_over_the_average() -> None:
    got = forecast(CELL, some(4), FIRST + dt.timedelta(days=3))
    assert got.loads_left == 30


def test_the_days_left_are_the_room_over_the_rate() -> None:
    got = forecast(CELL, some(4), FIRST + dt.timedelta(days=3))
    assert got.days_left == 6
    assert got.full_on == FIRST + dt.timedelta(days=9)


def test_a_full_cell_has_nothing_left() -> None:
    got = forecast(CELL, some(10), FIRST + dt.timedelta(days=9))
    assert got.remaining == Yards.zero()
    assert got.days_left == 0
    assert got.loads_left == 0


def test_an_ocean_site_has_nothing_to_run_out_of() -> None:
    got = forecast(OCEAN, [a_ticket(1, FIRST, area="PA-002")], FIRST)
    assert got.open_ground
    assert got.remaining is None
    assert got.days_left is None
    assert got.full_on is None


def test_tickets_for_another_area_are_not_counted() -> None:
    got = forecast(CELL, [a_ticket(1, FIRST, area="PA-002")], FIRST)
    assert got.loads == 0


def test_a_forecast_before_the_first_ticket_is_refused() -> None:
    with pytest.raises(FieldError):
        forecast(CELL, some(2), FIRST - dt.timedelta(days=1))


def test_a_longer_period_with_the_same_loads_gives_a_slower_rate() -> None:
    tickets = some(4)
    quick = forecast(CELL, tickets, FIRST + dt.timedelta(days=3))
    slow = forecast(CELL, tickets, FIRST + dt.timedelta(days=39))
    assert slow.a_day is not None
    assert quick.a_day is not None
    assert slow.a_day < quick.a_day
