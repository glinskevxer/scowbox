"""``scowbox report`` prints what the renderers built."""

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
    made(
        "placement", "add", "PA-002", "Wilmington ODMDS",
        "--ground", "ocean site", "--permit", "SAW-2019-01142",
    )  # fmt: skip
    made(
        "shift", "dredge", "DR-003", "Cherokee",
        "--plant", "mechanical", "--operator", "Norfolk Dredging",
    )  # fmt: skip
    return made


def test_an_empty_day_prints_the_empty_report(run: Book) -> None:
    out = run("report", "day", "--on", "2025-08-06")
    assert "Day report 2025-08-06" in out
    assert "No shift logged." in out


def test_a_day_with_work_prints_it(run: Book) -> None:
    run(
        "shift", "log", "SH-00021",
        "--dredge", "DR-003", "--reach", "RCH-012",
        "--on", "2025-08-06", "--from", "06:00", "--to", "18:00",
    )  # fmt: skip
    run(
        "trip", "add", "TR-04188",
        "--scow", "SC-004", "--reach", "RCH-012",
        "--on", "2025-08-06", "--to", "PA-002",
    )  # fmt: skip
    out = run("report", "day", "--on", "2025-08-06")
    assert "SH-00021" in out
    assert "TR-04188" in out
    assert "no placement ticket" in out


def test_the_reach_report_prints_the_template(run: Book) -> None:
    out = run("report", "reach", "RCH-012")
    assert "Reach RCH-012  Lower Range" in out
    assert "measured by   scow" in out


def test_the_reach_report_on_a_reach_that_is_not_there_fails(run: Book) -> None:
    run("report", "reach", "RCH-999", ok=False)
