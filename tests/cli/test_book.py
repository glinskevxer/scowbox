"""``scowbox book`` verifies, counts, copies and compacts."""

from __future__ import annotations

from pathlib import Path

import pytest

from scowbox.store.migrations import latest
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
    assert f"schema     version {latest()} of {latest()}" in run("book", "verify")


def test_the_counts_add_up_to_a_total(run: Book) -> None:
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


def test_compacting_a_small_book_reports_either_way(run: Book) -> None:
    out = run("book", "compact")
    assert "bytes recovered" in out or "too small to gain by it" in out


def test_compacting_a_book_with_room_in_it_recovers_bytes(run: Book) -> None:
    for number in range(200):
        run(
            "reach", "add", f"RCH-{number + 20:03d}", "Spare",
            "--begin", "100+00", "--end", "140+00", "--bottom", "400", "--depth", "42",
        )  # fmt: skip
    for number in range(200):
        run("reach", "remove", f"RCH-{number + 20:03d}")
    assert "bytes recovered" in run("book", "compact")


def test_the_laws_print_one_a_line(run: Book) -> None:
    out = run("book", "laws")
    assert "depths" in out
    assert "positive downward" in out
    assert "scowbox." not in out


def test_the_laws_can_name_where_they_live(run: Book) -> None:
    out = run("book", "laws", "--where")
    assert "scowbox.units.depth" in out


def test_the_laws_can_be_narrowed_to_a_word(run: Book) -> None:
    out = run("book", "laws", "--about", "prism")
    assert "prism" in out
    assert "depths" not in out


def test_a_word_no_rule_mentions_says_so(run: Book) -> None:
    assert "no rule mentions" in run("book", "laws", "--about", "fathoms")
