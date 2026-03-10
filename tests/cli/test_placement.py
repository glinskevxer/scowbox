"""``scowbox placement`` reports what each area takes and holds."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.cli.runner import Book, a_book

OCEAN = [
    "placement", "add", "PA-002", "Wilmington ODMDS",
    "--ground", "ocean site", "--permit", "SAW-2019-01142",
]  # fmt: skip
CELL = [
    "placement", "add", "PA-004", "Eagle Island cell 3",
    "--ground", "confined disposal", "--permit", "SAW-2019-01143",
    "--capacity", "500000",
]  # fmt: skip


@pytest.fixture
def run(tmp_path: Path) -> Book:
    return a_book(tmp_path)


def test_an_empty_book_says_so(run: Book) -> None:
    assert "no placement areas" in run("placement", "list")


def test_an_added_area_names_its_permit(run: Book) -> None:
    out = run(*OCEAN)
    assert "PA-002 Wilmington ODMDS, ocean site, permit SAW-2019-01142" in out


def test_an_open_site_lists_as_open(run: Book) -> None:
    run(*OCEAN)
    assert "open" in run("placement", "list")


def test_a_confined_facility_lists_the_room_left(run: Book) -> None:
    run(*CELL)
    assert "500,000.00 cy left" in run("placement", "list")


def test_a_confined_facility_needs_a_capacity(run: Book) -> None:
    run(*CELL[:-2], ok=False)


def test_show_reports_what_the_ground_takes(run: Book) -> None:
    run(*OCEAN)
    out = run("placement", "show", "PA-002")
    assert "ground     ocean site" in out
    assert "beach quality, suitable" in out
    assert "capacity   open" in out


def test_show_reports_the_share_used_on_a_cell(run: Book) -> None:
    run(*CELL)
    out = run("placement", "show", "PA-004")
    assert "0.0% used" in out


def test_an_area_that_is_not_there_fails(run: Book) -> None:
    run("placement", "show", "PA-009", ok=False)


def test_the_same_area_twice_is_refused(run: Book) -> None:
    run(*OCEAN)
    run(*OCEAN, ok=False)


def test_an_ocean_site_forecasts_nothing_to_run_out_of(run: Book) -> None:
    run(*OCEAN)
    out = run("placement", "forecast", "PA-002", "--through", "2026-01-05")
    assert "capacity   open, nothing to run out of" in out


def test_an_empty_cell_has_no_rate_to_forecast_from(run: Book) -> None:
    run(*CELL)
    out = run("placement", "forecast", "PA-004", "--through", "2026-01-05")
    assert "loads      0 over 0 days" in out
    assert "not enough days of tickets" in out


def test_an_area_that_is_not_there_cannot_be_forecast(run: Book) -> None:
    run("placement", "forecast", "PA-009", "--through", "2026-01-05", ok=False)
