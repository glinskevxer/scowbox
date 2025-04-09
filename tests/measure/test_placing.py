"""Grade first, then capacity."""

from __future__ import annotations

import datetime as dt

import pytest

from scowbox.errors import RuleError
from scowbox.measure.placing import check, standing, would_fill
from scowbox.model.placement import Grade, Ground, PlacementArea, PlacementTicket
from scowbox.units.clock import moment
from scowbox.units.volume import Yards

DAY = dt.date(2025, 4, 2)

OCEAN = PlacementArea("PA-002", "Wilmington ODMDS", Ground.OCEAN, "SAW-2019-01142")
CELL = PlacementArea(
    "PA-004", "Eagle Island cell 3", Ground.UPLAND, "SAW-2019-01143", Yards.of_yards(10000)
)
BEACH = PlacementArea("PA-006", "Kure template", Ground.BEACH, "SAW-2020-00981")


def a_ticket(area: str, yards: float, grade: Grade = Grade.SUITABLE) -> PlacementTicket:
    return PlacementTicket("TR-04188", area, moment(DAY, "11:20"), Yards.of_yards(yards), grade)


def test_an_empty_area_holds_nothing() -> None:
    held = standing(CELL, [])
    assert held.placed == Yards.zero()
    assert held.remaining == Yards.of_yards(10000)
    assert held.tickets == 0


def test_tickets_for_other_areas_are_not_counted() -> None:
    held = standing(CELL, [a_ticket("PA-002", 5000), a_ticket("PA-004", 1000)])
    assert held.placed == Yards.of_yards(1000)
    assert held.tickets == 1


def test_a_site_with_no_capacity_has_no_remainder() -> None:
    held = standing(OCEAN, [a_ticket("PA-002", 5000)])
    assert held.remaining is None
    assert held.share_used is None
    assert not held.full


def test_the_share_used_climbs_with_the_tickets() -> None:
    held = standing(CELL, [a_ticket("PA-004", 2500)])
    assert held.share_used == 0.25


def test_a_cell_filled_to_its_capacity_is_full() -> None:
    held = standing(CELL, [a_ticket("PA-004", 10000)])
    assert held.full
    assert held.remaining == Yards.zero()


def test_a_load_that_fits_passes() -> None:
    check(CELL, standing(CELL, []), Grade.UNSUITABLE, Yards.of_yards(1000))


def test_a_load_past_the_capacity_is_refused() -> None:
    held = standing(CELL, [a_ticket("PA-004", 9500)])
    with pytest.raises(RuleError, match="has 500.00 cy left"):
        check(CELL, held, Grade.SUITABLE, Yards.of_yards(1000))


def test_the_refusal_names_the_permit() -> None:
    held = standing(CELL, [a_ticket("PA-004", 9500)])
    with pytest.raises(RuleError, match="SAW-2019-01143"):
        check(CELL, held, Grade.SUITABLE, Yards.of_yards(1000))


def test_the_wrong_grade_is_refused_before_capacity_is_looked_at() -> None:
    held = standing(BEACH, [])
    with pytest.raises(RuleError, match="does not take unsuitable material"):
        check(BEACH, held, Grade.UNSUITABLE, Yards.of_yards(1_000_000))


def test_a_full_cell_refuses_on_capacity_not_on_grade() -> None:
    held = standing(CELL, [a_ticket("PA-004", 10000)])
    with pytest.raises(RuleError, match="left under permit"):
        check(CELL, held, Grade.UNSUITABLE, Yards.of_yards(1))


def test_would_fill_sees_the_load_that_closes_a_cell() -> None:
    held = standing(CELL, [a_ticket("PA-004", 9500)])
    assert would_fill(held, Yards.of_yards(500))
    assert not would_fill(held, Yards.of_yards(499))


def test_an_open_site_is_never_filled() -> None:
    assert not would_fill(standing(OCEAN, []), Yards.of_yards(1_000_000))
