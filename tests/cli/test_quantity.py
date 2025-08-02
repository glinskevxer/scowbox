"""``scowbox quantity`` reports what the book can measure."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.cli.runner import Book, a_book


@pytest.fixture
def run(tmp_path: Path) -> Book:
    made = a_book(tmp_path)
    made(
        "reach", "add", "RCH-012", "Lower Range",
        "--begin", "100+00", "--end", "103+00",
        "--bottom", "600", "--depth", "42", "--slope", "0",
        "--advance", "2", "--overdepth", "2",
    )  # fmt: skip
    return made


def load_tide(run: Book, tmp_path: Path, day: str) -> None:
    where = tmp_path / f"gauge-{day}.csv"
    where.write_text(
        f"Date Time,Water Level,Quality\n{day} 06:54,2.000,v\n{day} 07:06,2.000,v\n",
        encoding="utf-8",
    )
    run("tide", "load", "8658120", str(where))


def load_survey(run: Book, tmp_path: Path, ident: str, kind: str, day: str, depth: float) -> None:
    run(
        "survey", "add", ident, "RCH-012",
        "--kind", kind, "--on", day,
        "--vessel", "Cape Fear", "--draft", "2.0", "--gauge", "8658120",
    )  # fmt: skip
    where = tmp_path / f"shots-{ident}.csv"
    rows = [
        f"{station},{offset},{depth},07:00"
        for station in ("100+00", "101+00", "102+00", "103+00")
        for offset in (-300, 0, 300)
    ]
    where.write_text("station,offset,depth,time\n" + "\n".join(rows) + "\n", encoding="utf-8")
    run("survey", "load", ident, str(where))


@pytest.fixture
def measured(run: Book, tmp_path: Path) -> Book:
    load_tide(run, tmp_path, "2025-07-01")
    load_tide(run, tmp_path, "2025-08-01")
    load_survey(run, tmp_path, "SV-0031", "before", "2025-07-01", 38.0)
    load_survey(run, tmp_path, "SV-0032", "after", "2025-08-01", 42.0)
    return run


def test_a_measured_reach_reports_its_quantity(measured: Book) -> None:
    out = measured("quantity", "reach", "RCH-012")
    assert "measured by survey" in out
    assert "governs    survey" in out
    assert "26,667 cy" in out


def test_a_reach_with_no_scow_measure_says_so(measured: Book) -> None:
    assert "scow       not taken" in measured("quantity", "reach", "RCH-012")


def test_groups_gather_the_quantities(measured: Book) -> None:
    out = measured("quantity", "groups")
    assert "base" in out
    assert "26,667 cy" in out


def test_an_unmeasured_book_says_nothing_is_measured(run: Book) -> None:
    assert "nothing measured yet" in run("quantity", "groups")


def test_gaps_name_the_reach_and_the_reason(run: Book) -> None:
    out = run("quantity", "gaps")
    assert "RCH-012" in out
    assert "survey" in out


def test_a_measured_book_has_no_gaps(measured: Book) -> None:
    assert "every reach is measured" in measured("quantity", "gaps")


def test_a_reach_that_is_not_there_fails(measured: Book) -> None:
    measured("quantity", "reach", "RCH-999", ok=False)
