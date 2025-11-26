"""``scowbox reconcile`` settles a reach and puts it back in dispute."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.cli.runner import Book, a_book

SETTLE = [
    "reconcile", "settle", "RCH-012",
    "--accept", "survey", "--on", "2025-11-04", "--by", "R. Beaufort",
]  # fmt: skip


@pytest.fixture
def run(tmp_path: Path) -> Book:
    made = a_book(tmp_path)
    made(
        "reach", "add", "RCH-012", "Lower Range",
        "--begin", "100+00", "--end", "140+00",
        "--bottom", "400", "--depth", "42", "--method", "both",
    )  # fmt: skip
    return made


def test_an_empty_book_has_no_reconciliations(run: Book) -> None:
    assert "no reconciliations" in run("reconcile", "list")


def test_a_settlement_describes_itself(run: Book) -> None:
    out = run(*SETTLE)
    assert "RCH-012 settled 2025-11-04 by R. Beaufort: survey" in out


def test_a_settlement_shows_up_in_the_list(run: Book) -> None:
    run(*SETTLE)
    assert "RCH-012" in run("reconcile", "list")


def test_an_agreed_figure_needs_a_quantity_and_a_note(run: Book) -> None:
    run("reconcile", "settle", "RCH-012", "--accept", "agreed figure",
        "--on", "2025-11-04", "--by", "R. Beaufort", ok=False)  # fmt: skip


def test_an_agreed_figure_carries_both(run: Book) -> None:
    out = run(
        "reconcile", "settle", "RCH-012", "--accept", "agreed figure",
        "--on", "2025-11-04", "--by", "R. Beaufort",
        "--quantity", "24000", "--note", "split the difference",
    )  # fmt: skip
    assert "agreed figure, 24,000 cy" in out
    assert "split the difference" in run("reconcile", "list")


def test_settling_twice_is_refused(run: Book) -> None:
    run(*SETTLE)
    run(*SETTLE, ok=False)


def test_replacing_is_allowed_when_it_is_asked_for(run: Book) -> None:
    run(*SETTLE)
    out = run(*SETTLE[:4], "scow", *SETTLE[5:], "--replace")
    assert "scow" in out


def test_a_reach_that_is_not_there_cannot_be_settled(run: Book) -> None:
    run("reconcile", "settle", "RCH-999", "--accept", "survey",
        "--on", "2025-11-04", "--by", "R. Beaufort", ok=False)  # fmt: skip


def test_dropping_puts_the_reach_back_in_dispute(run: Book) -> None:
    run(*SETTLE)
    assert "back in dispute" in run("reconcile", "drop", "RCH-012")
    assert "no reconciliations" in run("reconcile", "list")


def test_dropping_what_is_not_there_fails(run: Book) -> None:
    run("reconcile", "drop", "RCH-012", ok=False)


def test_nothing_is_outstanding_on_an_unmeasured_book(run: Book) -> None:
    assert "nothing outstanding" in run("reconcile", "open")
