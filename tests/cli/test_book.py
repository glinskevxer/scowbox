"""``scowbox book`` verifies, counts, copies and compacts."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.cli.runner import Book, a_book


@pytest.fixture
def run(tmp_path: Path) -> Book:
    made = a_book(tmp_path)
    made(
        "reach", "add", "RCH-012", "Lower Range",
        "--begin", "100+00", "--end", "140+00", "--bottom", "400", "--depth", "42",
    )  # fmt: skip
    return made


def test_a_fresh_book_verifies(run: Book) -> None:
    out = run("book", "verify")
    assert "integrity  ok" in out
    assert "sound" in out


def test_verify_names_the_schema_version(run: Book) -> None:
    assert "schema     version 9 of 9" in run("book", "verify")


def test_counts_add_up(run: Book) -> None:
    out = run("book", "counts")
    assert "reach" in out
    assert "total" in out


def test_a_backup_lands_where_it_was_asked_to(run: Book, tmp_path: Path) -> None:
    where = tmp_path / "copy.sqlite3"
    assert "copied to" in run("book", "backup", str(where))
    assert where.exists()


def test_a_backup_over_something_is_refused(run: Book, tmp_path: Path) -> None:
    where = tmp_path / "copy.sqlite3"
    run("book", "backup", str(where))
    run("book", "backup", str(where), ok=False)


def test_the_copy_is_a_book_in_its_own_right(run: Book, tmp_path: Path) -> None:
    where = tmp_path / "copy.sqlite3"
    run("book", "backup", str(where))
    assert "RCH-012" in Book(where)("reach", "list")


def test_compacting_a_small_book_says_what_it_cost(run: Book) -> None:
    assert "too small to gain by it" in run("book", "compact")


def test_compacting_a_book_with_room_in_it_recovers_bytes(run: Book) -> None:
    for number in range(200):
        run(
            "reach", "add", f"RCH-{number + 20:03d}", "Spare",
            "--begin", "100+00", "--end", "140+00", "--bottom", "400", "--depth", "42",
        )  # fmt: skip
    for number in range(200):
        run("reach", "remove", f"RCH-{number + 20:03d}")
    assert "bytes recovered" in run("book", "compact")
