"""``scowbox contract`` builds a bid schedule a line at a time."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.cli.runner import Book, a_book

CONTRACT = [
    "contract", "add", "W912PM-25-C-0014",
    "--awarded", "2025-01-20", "--ntp", "2025-02-03",
    "--days", "365", "--retainage", "0.05", "--liquidated", "$3,400.00",
]  # fmt: skip


@pytest.fixture
def run(tmp_path: Path) -> Book:
    made = a_book(tmp_path)
    made(*CONTRACT)
    return made


def test_adding_reports_the_completion_day(run: Book) -> None:
    assert "365 days, complete 2026-02-03" in run("contract", "show")


def test_a_book_with_no_contract_cannot_show_one(tmp_path: Path) -> None:
    a_book(tmp_path, "empty.sqlite3")("contract", "show", ok=False)


def test_an_item_prices_itself(run: Book) -> None:
    out = run(
        "contract", "item", "LI-0001", "Dredging, base",
        "--unit", "cy", "--price", "$7.35", "--group", "base",
    )  # fmt: skip
    assert "at $7.35 per cy" in out


def test_a_cubic_yard_item_needs_a_pay_group(run: Book) -> None:
    run(
        "contract", "item", "LI-0001", "Dredging, base",
        "--unit", "cy", "--price", "$7.35", ok=False,
    )  # fmt: skip


def test_a_lump_sum_with_a_pay_group_is_refused(run: Book) -> None:
    run(
        "contract", "item", "LI-0009", "Mobilisation",
        "--unit", "ls", "--price", "$1.00", "--group", "base", ok=False,
    )  # fmt: skip


def test_two_items_on_one_pay_group_are_refused(run: Book) -> None:
    run(
        "contract", "item", "LI-0001", "Dredging, base",
        "--unit", "cy", "--price", "$7.35", "--group", "base",
    )  # fmt: skip
    run(
        "contract", "item", "LI-0002", "Dredging, base again",
        "--unit", "cy", "--price", "$8.35", "--group", "base", ok=False,
    )  # fmt: skip


def test_the_schedule_shows_every_line(run: Book) -> None:
    run(
        "contract", "item", "LI-0001", "Dredging, base",
        "--unit", "cy", "--price", "$7.35", "--group", "base",
    )  # fmt: skip
    run(
        "contract", "item", "LI-0009", "Mobilisation",
        "--unit", "ls", "--price", "$1,250,000.00",
    )  # fmt: skip
    out = run("contract", "show")
    assert "LI-0001" in out
    assert "LI-0009" in out
    assert "$1,250,000.00" in out


def test_the_terms_are_printed(run: Book) -> None:
    out = run("contract", "show")
    assert "retainage  5.0%" in out
    assert "damages    $3,400.00 per day" in out
