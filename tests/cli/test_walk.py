"""One job through the command line, the way the CI walk does it.

The other command line suites test a command at a time against a book somebody
set up for them. This sets nothing up: every record is typed, in order, and the
last command has to agree with the first. It is slower than the rest of the
suite put together and it has caught two things nothing else did, both of them
a command that worked and left the book in a state the next command could not
use.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.cli.runner import Book, a_book
from tests.cli.surveying import a_reach, survey_the_reach


@pytest.fixture(scope="module")
def walked(tmp_path_factory: pytest.TempPathFactory) -> Book:
    """A whole job, typed once."""
    where = tmp_path_factory.mktemp("walk")
    run = a_book(where)
    run(
        "contract", "add", "W912PM-25-C-0014",
        "--awarded", "2025-01-20", "--ntp", "2025-02-03",
        "--days", "730", "--liquidated", "$3,400.00",
    )  # fmt: skip
    run(
        "contract", "item", "LI-0001", "Maintenance dredging, base",
        "--unit", "cy", "--price", "$7.35", "--group", "base", "--estimated", "480000",
    )  # fmt: skip
    a_reach(run, method="both")
    survey_the_reach(run, where)
    run("scow", "add", "SC-004", "Dixie 41", "--length", "180", "--width", "42", "--depth", "14")
    run(
        "placement", "add", "PA-002", "Wilmington ODMDS",
        "--ground", "ocean site", "--permit", "SAW-2019-01142",
    )  # fmt: skip
    run(
        "shift", "dredge", "DR-003", "Cherokee",
        "--plant", "mechanical", "--operator", "Norfolk Dredging",
    )  # fmt: skip
    run(
        "shift", "log", "SH-00021", "--dredge", "DR-003", "--reach", "RCH-012",
        "--on", "2025-07-14", "--from", "06:00", "--to", "18:00",
    )  # fmt: skip
    run("shift", "stop", "SH-00021", "--from", "06:00", "--to", "13:00", "--reason", "weather")
    for number in range(1, 15):
        ident = f"TR-{number:05d}"
        run(
            "trip", "add", ident, "--scow", "SC-004", "--reach", "RCH-012",
            "--on", "2025-07-14", "--to", "PA-002",
        )  # fmt: skip
        run(
            "trip", "measure", ident,
            "--light", "12", "--pb", "4", "--sb", "4", "--ps", "4", "--ss", "4",
        )  # fmt: skip
        run(
            "trip", "release", ident, "--at", "PA-002",
            "--on", "2025-07-14", "--time", "11:20", "--grade", "suitable",
        )  # fmt: skip
    return run


def test_the_reach_is_measured_both_ways(walked: Book) -> None:
    out = walked("quantity", "reach", "RCH-012")
    assert "measured by both" in out
    assert "governs    survey" in out
    assert "26,667 cy" in out


def test_the_two_measurements_land_inside_the_tolerance(walked: Book) -> None:
    assert "nothing outstanding" in walked("reconcile", "open")


def test_every_trip_is_ticketed(walked: Book) -> None:
    assert "every trip is ticketed" in walked("trip", "open")


def test_the_weather_day_is_credited(walked: Book) -> None:
    out = walked("shift", "time", "--from", "2025-07-01", "--to", "2025-07-31")
    assert "days earned  1" in out


def test_the_book_verifies_as_sound(walked: Book) -> None:
    assert "sound" in walked("book", "verify")


def test_the_day_report_holds_the_whole_day(walked: Book) -> None:
    out = walked("report", "day", "--on", "2025-07-14")
    assert "SH-00021" in out
    assert "TR-00001" in out
    assert "Nothing outstanding." in out


def test_the_season_report_prices_the_quantity(walked: Book) -> None:
    out = walked("report", "season")
    assert "26,667 cy" in out
    assert "$196,000" in out


def test_the_fleet_and_production_reports_print(walked: Book) -> None:
    assert "SC-004" in walked("report", "fleet")
    assert "cy per hour" in walked("report", "production")


def test_the_closeout_has_nothing_in_the_way(walked: Book) -> None:
    out = walked("report", "closeout")
    assert "outstanding   0" in out
    assert "The final estimate can be written." in out


def test_the_export_writes_every_sheet(walked: Book, tmp_path: Path) -> None:
    out = walked("report", "export", str(tmp_path / "out"))
    assert "reaches.csv" in out
    assert (tmp_path / "out" / "trips.csv").exists()


def test_the_find_command_reaches_every_family(walked: Book) -> None:
    assert "Lower Range" in walked("find", "RCH-012")
    assert "released at PA-002" in walked("find", "TR-00001")
    assert "readings from" in walked("find", "8658120")
