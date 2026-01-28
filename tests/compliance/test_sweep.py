"""The sweep, over records that are there rather than records that should be."""

from __future__ import annotations

import datetime as dt

from scowbox.compliance.findings import Severity
from scowbox.compliance.sweep import (
    shifts_against_windows,
    sweep,
    tickets_against_areas,
    trips_without_tickets,
)
from scowbox.model.placement import Grade, Ground, PlacementArea, PlacementTicket
from scowbox.model.scow import ScowTrip
from scowbox.model.shift import Shift
from scowbox.model.window import Restriction, Window
from scowbox.units.clock import moment
from scowbox.units.volume import Yards
from scowbox.windows.schedule import Schedule

DAY = dt.date(2025, 6, 4)
OCEAN = PlacementArea("PA-002", "Wilmington ODMDS", Ground.OCEAN, "SAW-2019-01142")
BEACH = PlacementArea("PA-006", "Kure template", Ground.BEACH, "SAW-2020-00981")
CELL = PlacementArea(
    "PA-004", "Eagle Island cell 3", Ground.UPLAND, "SAW-2019-01143", Yards.of_yards(2000)
)
AREAS = {a.ident: a for a in (OCEAN, BEACH, CELL)}


def a_shift(reach: str = "RCH-012", day: dt.date = DAY) -> Shift:
    return Shift("SH-00021", "DR-003", reach, moment(day, "06:00"), moment(day, "18:00"))


def a_trip(ident: str = "TR-04188", day: dt.date = DAY) -> ScowTrip:
    return ScowTrip(ident, "SC-004", "RCH-012", day, "PA-002")


def a_ticket(
    trip: str = "TR-04188",
    area: str = "PA-002",
    grade: Grade = Grade.SUITABLE,
    yards: float = 1800,
) -> PlacementTicket:
    return PlacementTicket(trip, area, moment(DAY, "11:20"), Yards.of_yards(yards), grade)


def a_closure(restriction: Restriction = Restriction.CLOSED) -> Window:
    return Window("loggerhead", dt.date(2025, 5, 1), dt.date(2025, 11, 30), restriction, "NMFS")


def test_clean_records_sweep_clean() -> None:
    got = sweep([a_shift()], [a_trip()], [a_ticket()], AREAS, Schedule.of([]))
    assert got.clean
    assert (got.shifts, got.trips, got.tickets) == (1, 1, 1)


def test_working_inside_a_closure_is_a_violation() -> None:
    got = sweep([a_shift()], [], [], AREAS, Schedule.of([a_closure()]))
    assert got.findings[0].severity is Severity.VIOLATION
    assert "loggerhead" in got.findings[0].detail


def test_working_inside_an_observer_window_is_a_warning() -> None:
    got = sweep([a_shift()], [], [], AREAS, Schedule.of([a_closure(Restriction.OBSERVER)]))
    assert got.findings[0].severity is Severity.WARNING


def test_a_shift_outside_every_window_is_nothing() -> None:
    early = a_shift(day=dt.date(2025, 4, 1))
    assert sweep([early], [], [], AREAS, Schedule.of([a_closure()])).clean


def test_the_wrong_grade_at_a_beach_is_a_violation() -> None:
    got = sweep([], [a_trip()], [a_ticket(area="PA-006")], AREAS, Schedule.of([]))
    assert got.findings[0].kind == "placement"
    assert got.findings[0].severity is Severity.VIOLATION


def test_beach_quality_sand_at_a_beach_is_fine() -> None:
    ticket = a_ticket(area="PA-006", grade=Grade.BEACH_QUALITY)
    assert sweep([], [a_trip()], [ticket], AREAS, Schedule.of([])).clean


def test_a_ticket_for_an_area_that_is_not_there_is_a_violation() -> None:
    got = sweep([], [a_trip()], [a_ticket(area="PA-009")], AREAS, Schedule.of([]))
    assert "not a placement area" in got.findings[0].detail


def test_a_cell_at_capacity_is_a_warning() -> None:
    filled = a_ticket(area="PA-004", grade=Grade.UNSUITABLE, yards=2000)
    got = sweep([], [a_trip()], [filled], AREAS, Schedule.of([]))
    assert [f.kind for f in got.findings] == ["capacity"]
    assert got.findings[0].severity is Severity.WARNING


def test_a_trip_with_no_ticket_is_a_warning_while_the_month_is_open() -> None:
    got = sweep([], [a_trip()], [], AREAS, Schedule.of([]))
    assert got.findings[0].kind == "ticket"
    assert got.findings[0].severity is Severity.WARNING


def test_a_trip_with_no_ticket_is_a_violation_once_the_month_closes() -> None:
    got = sweep([], [a_trip()], [], AREAS, Schedule.of([]), closed_through=dt.date(2025, 6, 30))
    assert got.findings[0].severity is Severity.VIOLATION


def test_a_trip_loaded_after_the_close_is_still_only_a_warning() -> None:
    late = a_trip(day=dt.date(2025, 7, 2))
    got = sweep([], [late], [], AREAS, Schedule.of([]), closed_through=dt.date(2025, 6, 30))
    assert got.findings[0].severity is Severity.WARNING


def test_findings_come_back_worst_first() -> None:
    got = sweep(
        [a_shift()],
        [a_trip("TR-04188"), a_trip("TR-04190")],
        [a_ticket("TR-04188")],
        AREAS,
        Schedule.of([a_closure()]),
    )
    assert got.findings[0].severity is Severity.VIOLATION
    assert got.findings[-1].severity is Severity.WARNING


def test_the_window_check_can_be_run_on_its_own() -> None:
    found = shifts_against_windows([a_shift()], Schedule.of([a_closure()]))
    assert len(found) == 1
    assert found[0].kind == "window"


def test_the_placement_check_can_be_run_on_its_own() -> None:
    found = tickets_against_areas([a_ticket(area="PA-006")], AREAS)
    assert found[0].kind == "placement"


def test_the_ticket_check_can_be_run_on_its_own() -> None:
    found = trips_without_tickets([a_trip()], [])
    assert found[0].kind == "ticket"
    assert trips_without_tickets([a_trip()], ["TR-04188"]) == ()
