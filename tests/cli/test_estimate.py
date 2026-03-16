"""``scowbox contract`` and ``scowbox estimate`` end to end."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.cli.runner import Book, a_book
from tests.cli.surveying import a_reach, survey_the_reach


@pytest.fixture
def run(tmp_path: Path) -> Book:
    made = a_book(tmp_path)
    made(
        "contract", "add", "W912PM-25-C-0014",
        "--awarded", "2025-01-20", "--ntp", "2025-02-03",
        "--days", "365", "--retainage", "0.05", "--liquidated", "$3,400.00",
    )  # fmt: skip
    made(
        "contract", "item", "LI-0001", "Dredging, base",
        "--unit", "cy", "--price", "$7.35", "--group", "base", "--estimated", "480000",
    )  # fmt: skip
    made(
        "contract", "item", "LI-0009", "Mobilisation",
        "--unit", "ls", "--price", "$1,250,000.00",
    )  # fmt: skip
    a_reach(made)
    return made


def test_the_contract_shows_its_schedule(run: Book) -> None:
    out = run("contract", "show")
    assert "W912PM-25-C-0014" in out
    assert "LI-0001" in out
    assert "LI-0009" in out
    assert "retainage  5.0%" in out


def test_a_draft_prices_the_measured_quantity(run: Book, tmp_path: Path) -> None:
    survey_the_reach(run, tmp_path)
    out = run("estimate", "draft", "--through", "2025-08-31")
    assert "EST-001" in out
    assert "26,666.67" in out
    assert "$196,000.02" in out


def test_a_draft_is_not_written(run: Book, tmp_path: Path) -> None:
    survey_the_reach(run, tmp_path)
    run("estimate", "draft", "--through", "2025-08-31")
    assert "no estimates" in run("estimate", "list")


def test_writing_puts_it_in_the_book(run: Book, tmp_path: Path) -> None:
    survey_the_reach(run, tmp_path)
    run("estimate", "write", "--through", "2025-08-31")
    assert "EST-001" in run("estimate", "list")


def test_a_claimed_lump_sum_reaches_the_line(run: Book, tmp_path: Path) -> None:
    survey_the_reach(run, tmp_path)
    out = run("estimate", "draft", "--through", "2025-08-31", "--claim", "LI-0009=1.0")
    assert "$1,250,000.00" in out


def test_a_badly_written_claim_is_refused(run: Book, tmp_path: Path) -> None:
    survey_the_reach(run, tmp_path)
    run("estimate", "draft", "--through", "2025-08-31", "--claim", "LI-0009", ok=False)


def test_an_unmeasured_reach_is_reported_on_the_draft(run: Book) -> None:
    out = run("estimate", "draft", "--through", "2025-08-31")
    assert "not measured: RCH-012" in out


def test_the_second_estimate_shows_only_the_difference(run: Book, tmp_path: Path) -> None:
    survey_the_reach(run, tmp_path)
    run("estimate", "write", "--through", "2025-08-31")
    out = run("estimate", "draft", "--through", "2025-09-30")
    assert "estimate 2" in out
    assert "paid before" in out


def test_an_estimate_cannot_run_back_over_the_last_one(run: Book, tmp_path: Path) -> None:
    survey_the_reach(run, tmp_path)
    run("estimate", "write", "--through", "2025-08-31")
    run("estimate", "write", "--through", "2025-08-31", ok=False)


def test_a_written_estimate_can_be_shown_again(run: Book, tmp_path: Path) -> None:
    survey_the_reach(run, tmp_path)
    run("estimate", "write", "--through", "2025-08-31")
    assert "26,666.67" in run("estimate", "show", "EST-001")


def test_liquidated_damages_show_on_a_late_estimate(run: Book, tmp_path: Path) -> None:
    survey_the_reach(run, tmp_path)
    out = run("estimate", "draft", "--through", "2026-02-13")
    assert "damages" in out
    assert "10 days" in out
