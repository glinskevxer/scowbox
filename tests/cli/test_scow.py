"""``scowbox scow`` and ``scowbox trip`` through a real book."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.cli.runner import Book, a_book


@pytest.fixture
def run(tmp_path: Path) -> Book:
    made = a_book(tmp_path)
    made(
        "reach", "add", "RCH-012", "Lower Range",
        "--begin", "100+00", "--end", "140+00",
        "--bottom", "400", "--depth", "42", "--method", "scow",
    )  # fmt: skip
    made("scow", "add", "SC-004", "Dixie 41", "--length", "180", "--width", "42", "--depth", "14")
    return made


def a_trip(run: Book, ident: str = "TR-04188") -> None:
    run(
        "trip", "add", ident,
        "--scow", "SC-004", "--reach", "RCH-012",
        "--on", "2025-06-04", "--to", "PA-002",
    )  # fmt: skip


def test_an_added_scow_shows_up(run: Book) -> None:
    assert "SC-004 Dixie 41" in run("scow", "list")
    assert "7,560 sq ft" in run("scow", "list")


def test_an_empty_fleet_says_so(tmp_path: Path) -> None:
    fresh = a_book(tmp_path, "empty.sqlite3")
    assert "no scows" in fresh("scow", "list")


def test_a_trip_needs_a_placement_area_that_exists(run: Book) -> None:
    run(
        "trip", "add", "TR-04188",
        "--scow", "SC-004", "--reach", "RCH-012",
        "--on", "2025-06-04", "--to", "PA-002", ok=False,
    )  # fmt: skip


@pytest.fixture
def loaded(run: Book) -> Book:
    run(
        "placement", "add", "PA-002", "Wilmington ODMDS",
        "--ground", "ocean site", "--permit", "SAW-2019-01142",
    )  # fmt: skip
    a_trip(run)
    return run


def test_a_trip_starts_unmeasured_and_unticketed(loaded: Book) -> None:
    out = loaded("trip", "list")
    assert "unmeasured" in out
    assert "no ticket" in out


def test_measuring_reports_the_box(loaded: Book) -> None:
    out = loaded(
        "trip", "measure", "TR-04188",
        "--light", "12", "--pb", "4", "--sb", "4", "--ps", "4", "--ss", "4",
    )  # fmt: skip
    assert "mean 8.00 ft" in out
    assert "2,240.00 cy" in out


def test_a_wedge_is_called_out_as_suspect(loaded: Book) -> None:
    out = loaded(
        "trip", "measure", "TR-04188",
        "--light", "12", "--pb", "1", "--sb", "1", "--ps", "7", "--ss", "7",
    )  # fmt: skip
    assert "suspect: trim" in out


def test_releasing_writes_a_ticket_for_the_measured_load(loaded: Book) -> None:
    loaded(
        "trip", "measure", "TR-04188",
        "--light", "12", "--pb", "4", "--sb", "4", "--ps", "4", "--ss", "4",
    )  # fmt: skip
    out = loaded(
        "trip", "release", "TR-04188",
        "--at", "PA-002", "--on", "2025-06-04", "--time", "11:20", "--grade", "suitable",
    )  # fmt: skip
    assert "released at PA-002" in out
    assert "2,240.00 cy" in out


def test_an_unmeasured_trip_cannot_be_released(loaded: Book) -> None:
    loaded(
        "trip", "release", "TR-04188",
        "--at", "PA-002", "--on", "2025-06-04", "--time", "11:20", "--grade", "suitable",
        ok=False,
    )  # fmt: skip


def test_open_trips_are_listed_until_they_are_ticketed(loaded: Book) -> None:
    assert "TR-04188" in loaded("trip", "open")
    loaded(
        "trip", "measure", "TR-04188",
        "--light", "12", "--pb", "4", "--sb", "4", "--ps", "4", "--ss", "4",
    )  # fmt: skip
    loaded(
        "trip", "release", "TR-04188",
        "--at", "PA-002", "--on", "2025-06-04", "--time", "11:20", "--grade", "suitable",
    )  # fmt: skip
    assert "every trip is ticketed" in loaded("trip", "open")


def test_show_reports_the_whole_trip(loaded: Book) -> None:
    loaded(
        "trip", "measure", "TR-04188",
        "--light", "12", "--pb", "4", "--sb", "4", "--ps", "4", "--ss", "4",
    )  # fmt: skip
    out = loaded("trip", "show", "TR-04188")
    assert "scow       SC-004 Dixie 41" in out
    assert "box        mean 8.00 ft" in out
    assert "ticket     none" in out


def test_show_reports_an_unmeasured_trip_as_one(loaded: Book) -> None:
    assert "box        not measured" in loaded("trip", "show", "TR-04188")


def test_a_reach_filter_narrows_the_trip_list(loaded: Book) -> None:
    assert "TR-04188" in loaded("trip", "list", "--reach", "RCH-012")
    assert "no trips" in loaded("trip", "list", "--reach", "RCH-999")
