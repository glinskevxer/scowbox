"""Migrations run once, in order, and a newer book is refused."""

from __future__ import annotations

from pathlib import Path

import pytest

from scowbox.errors import StateError
from scowbox.store.migrations import MIGRATIONS, latest, migrate, pending, version_of
from scowbox.store.sqlite import opened, rows


def test_migration_numbers_are_distinct_and_in_order() -> None:
    numbers = [m.version for m in MIGRATIONS]
    assert numbers == sorted(numbers)
    assert len(set(numbers)) == len(numbers)


def test_migration_names_are_distinct() -> None:
    names = [m.name for m in MIGRATIONS]
    assert len(set(names)) == len(names)


def test_a_new_book_starts_at_nothing(tmp_path: Path) -> None:
    with opened(tmp_path / "book.sqlite3") as connection:
        assert version_of(connection) == 0
        assert len(pending(connection)) == len(MIGRATIONS)


def test_migrating_brings_a_book_to_the_latest(tmp_path: Path) -> None:
    with opened(tmp_path / "book.sqlite3") as connection:
        ran = migrate(connection)
        assert ran == tuple(m.name for m in MIGRATIONS)
        assert version_of(connection) == latest()


def test_migrating_twice_runs_nothing_the_second_time(tmp_path: Path) -> None:
    with opened(tmp_path / "book.sqlite3") as connection:
        migrate(connection)
        assert migrate(connection) == ()


def test_the_version_survives_closing_the_book(tmp_path: Path) -> None:
    book = tmp_path / "book.sqlite3"
    with opened(book) as connection:
        migrate(connection)
    with opened(book) as connection:
        assert version_of(connection) == latest()


def test_a_book_from_a_newer_program_is_refused(tmp_path: Path) -> None:
    with opened(tmp_path / "book.sqlite3") as connection:
        connection.execute(f"PRAGMA user_version = {latest() + 1}")
        with pytest.raises(StateError):
            migrate(connection)


def test_the_first_migration_makes_the_reach_table(tmp_path: Path) -> None:
    with opened(tmp_path / "book.sqlite3") as connection:
        migrate(connection)
        names = {r["name"] for r in rows(connection, "SELECT name FROM sqlite_master")}
        assert "reach" in names
        assert "reach_by_group" in names
