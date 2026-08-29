"""Reading a shift log and a trip sheet against each other."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.compliance.findings import Severity
from scowbox.job.preflight import (
    held_by,
    loads_scows,
    preflight,
    unhauled,
    unknown,
    unworked,
)
from scowbox.model.channel import Method, Reach, Template
from scowbox.model.placement import Ground, PlacementArea
from scowbox.model.plant import Dredge, Plant
from scowbox.model.scow import Scow, ScowTrip
from scowbox.model.shift import Shift
from scowbox.store import placements, reaches, scows, shifts
from scowbox.store.book import book
from scowbox.units.clock import moment
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline

DAY = dt.date(2026, 8, 28)
NEXT = dt.date(2026, 8, 29)


@pytest.fixture
def open_book(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with book(tmp_path / "book.sqlite3", create=True) as connection:
        reaches.add(
            connection,
            Reach(
                ident="RCH-012",
                name="Lower Range",
                line=Reachline.parse("100+00", "140+00"),
                template=Template(
                    bottom_width=400, authorized_depth=Depth.of_feet(42), side_slope=3
                ),
                method=Method.SCOW,
                group="base",
            ),
        )
        scows.add(connection, Scow("SC-004", "Dixie 41", 180, 42, 14))
        placements.add(
            connection,
            PlacementArea("PA-002", "Wilmington ODMDS", Ground.OCEAN, "SAW-2019-01142"),
        )
        shifts.add_dredge(
            connection, Dredge("DR-003", "Cherokee", Plant.MECHANICAL, "Norfolk Dredging")
        )
        shifts.add_dredge(connection, Dredge("DR-005", "Illinois", Plant.CUTTER, "Great Lakes"))
        yield connection


def a_shift(
    ident: str = "SH-00030", day: dt.date = DAY, dredge: str = "DR-003", reach: str = "RCH-012"
) -> Shift:
    return Shift(ident, dredge, reach, moment(day, "06:00"), moment(day, "18:00"))


def a_trip(
    ident: str = "TR-00030",
    day: dt.date = DAY,
    reach: str = "RCH-012",
    scow: str = "SC-004",
    placement: str = "PA-002",
) -> ScowTrip:
    return ScowTrip(ident, scow, reach, day, placement)


def test_a_matching_log_and_sheet_have_nothing_to_fix(
    open_book: sqlite3.Connection,
) -> None:
    found = preflight(open_book, [a_shift()], [a_trip()])
    assert found.clean
    assert (found.shifts, found.trips) == (1, 1)


def test_the_book_hands_back_what_it_can_resolve(open_book: sqlite3.Connection) -> None:
    held = held_by(open_book)
    assert held.reaches == frozenset({"RCH-012"})
    assert held.scows == frozenset({"SC-004"})
    assert held.areas == frozenset({"PA-002"})
    assert held.dredges == frozenset({"DR-003", "DR-005"})


def test_only_a_mechanical_dredge_is_expected_to_load_scows(
    open_book: sqlite3.Connection,
) -> None:
    assert loads_scows(open_book) == frozenset({"DR-003"})


def test_a_trip_on_a_day_with_no_shift_is_reported(
    open_book: sqlite3.Connection,
) -> None:
    found = preflight(open_book, [a_shift()], [a_trip(day=NEXT)])
    kinds = [f.kind for f in found.findings]
    assert "no shift" in kinds
    assert found.findings[0].severity is Severity.WARNING


def test_a_trip_out_of_another_reach_is_reported_too() -> None:
    found = unworked([a_shift()], [a_trip(reach="RCH-014")])
    assert found[0].kind == "no shift"
    assert "RCH-014" in found[0].detail


def test_a_mechanical_shift_with_no_trip_is_reported() -> None:
    found = unhauled([a_shift()], [], frozenset({"DR-003"}))
    assert found[0].kind == "no trip"
    assert "loads scows" in found[0].detail


def test_a_cutter_shift_with_no_trip_is_an_ordinary_day() -> None:
    assert unhauled([a_shift(dredge="DR-005")], [], frozenset({"DR-003"})) == []


def test_a_cutter_shift_is_left_alone_by_the_whole_pass(
    open_book: sqlite3.Connection,
) -> None:
    found = preflight(open_book, [a_shift(dredge="DR-005")], [])
    assert found.clean


def test_a_shift_naming_a_reach_the_book_has_not_blocks(
    open_book: sqlite3.Connection,
) -> None:
    found = preflight(open_book, [a_shift(reach="RCH-999")], [])
    assert found.blocking
    assert found.blocking[0].kind == "unknown reach"


def test_a_shift_naming_a_dredge_the_book_has_not_blocks(
    open_book: sqlite3.Connection,
) -> None:
    found = preflight(open_book, [a_shift(dredge="DR-009")], [])
    assert any(f.kind == "unknown dredge" for f in found.blocking)


def test_a_trip_naming_a_scow_the_book_has_not_blocks(
    open_book: sqlite3.Connection,
) -> None:
    found = preflight(open_book, [a_shift()], [a_trip(scow="SC-009")])
    assert any(f.kind == "unknown scow" for f in found.blocking)


def test_a_trip_naming_an_area_the_book_has_not_blocks(
    open_book: sqlite3.Connection,
) -> None:
    found = preflight(open_book, [a_shift()], [a_trip(placement="PA-009")])
    assert any(f.kind == "unknown placement area" for f in found.blocking)


def test_nothing_is_unknown_when_the_book_holds_it_all(
    open_book: sqlite3.Connection,
) -> None:
    assert unknown([a_shift()], [a_trip()], held_by(open_book)) == []


def test_one_record_can_name_two_absences_at_once(
    open_book: sqlite3.Connection,
) -> None:
    found = unknown([], [a_trip(scow="SC-009", placement="PA-009")], held_by(open_book))
    assert {f.kind for f in found} == {"unknown scow", "unknown placement area"}
    assert all(f.subject == "TR-00030" for f in found)


def test_the_worst_findings_come_first(open_book: sqlite3.Connection) -> None:
    found = preflight(open_book, [a_shift()], [a_trip(day=NEXT, scow="SC-009")])
    assert found.findings[0].severity is Severity.VIOLATION
    assert found.findings[-1].severity is Severity.WARNING


def test_two_empty_files_have_nothing_to_fix(open_book: sqlite3.Connection) -> None:
    found = preflight(open_book, [], [])
    assert found.clean
    assert (found.shifts, found.trips) == (0, 0)
