"""``scowbox modification`` records the signed changes."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.cli.runner import Book, a_book


@pytest.fixture
def run(tmp_path: Path) -> Book:
    made = a_book(tmp_path)
    made(
        "contract", "add", "W912PM-25-C-0014",
        "--awarded", "2025-01-20", "--ntp", "2025-02-03",
        "--days", "365", "--liquidated", "$3,400.00",
    )  # fmt: skip
    made(
        "contract", "item", "LI-0001", "Dredging, base",
        "--unit", "cy", "--price", "$7.35", "--group", "base",
    )  # fmt: skip
    return made


def test_an_empty_book_has_no_modifications(run: Book) -> None:
    assert "no modifications" in run("modification", "list")


def test_a_time_extension_describes_itself(run: Book) -> None:
    out = run(
        "modification", "add", "P00003", "--on", "2026-01-12",
        "--change", "contract time", "--description", "Sturgeon window", "--days", "45",
    )  # fmt: skip
    assert "contract time: +45 days" in out


def test_a_time_extension_moves_the_completion_day(run: Book) -> None:
    run(
        "modification", "add", "P00003", "--on", "2026-01-12",
        "--change", "contract time", "--description", "Sturgeon window", "--days", "45",
    )  # fmt: skip
    out = run("modification", "current")
    assert "410 days" in out
    assert "extended by   +45 days" in out


def test_a_price_change_reprices_the_line(run: Book) -> None:
    run(
        "modification", "add", "P00004", "--on", "2026-02-02",
        "--change", "unit price", "--description", "Rock",
        "--item", "LI-0001", "--price", "$9.10",
    )  # fmt: skip
    assert "$9.10" in run("modification", "current")


def test_a_new_item_joins_the_schedule(run: Book) -> None:
    run(
        "modification", "add", "P00007", "--on", "2026-03-02",
        "--change", "new line item", "--description", "Relocation trawling",
        "--item", "LI-0020", "--price", "$85,000.00",
    )  # fmt: skip
    assert "LI-0020" in run("modification", "current")


def test_a_time_extension_with_no_days_is_refused(run: Book) -> None:
    run(
        "modification", "add", "P00003", "--on", "2026-01-12",
        "--change", "contract time", "--description", "Sturgeon window", ok=False,
    )  # fmt: skip


def test_a_modification_shows_up_in_the_list(run: Book) -> None:
    run(
        "modification", "add", "P00003", "--on", "2026-01-12",
        "--change", "contract time", "--description", "Sturgeon window", "--days", "45",
    )  # fmt: skip
    out = run("modification", "list")
    assert "P00003" in out
    assert "Sturgeon window" in out


def test_dropping_one_takes_it_off_the_contract(run: Book) -> None:
    run(
        "modification", "add", "P00003", "--on", "2026-01-12",
        "--change", "contract time", "--description", "Sturgeon window", "--days", "45",
    )  # fmt: skip
    run("modification", "drop", "P00003")
    assert "365 days" in run("modification", "current")


def test_dropping_one_that_is_not_there_fails(run: Book) -> None:
    run("modification", "drop", "P00003", ok=False)
