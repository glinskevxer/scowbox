"""``scowbox quantity`` reports what the book can measure."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.cli.runner import Book, a_book
from tests.cli.surveying import a_reach, survey_the_reach


@pytest.fixture
def run(tmp_path: Path) -> Book:
    made = a_book(tmp_path)
    a_reach(made)
    return made


@pytest.fixture
def measured(run: Book, tmp_path: Path) -> Book:
    survey_the_reach(run, tmp_path)
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
