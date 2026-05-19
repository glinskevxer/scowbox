"""The index check, on this schema and on a table with a bare foreign key."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.store.book import book
from scowbox.tools.check_indexes import findings, foreign_keys, indexed, main, tables


@pytest.fixture
def open_book(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with book(tmp_path / "book.sqlite3", create=True) as connection:
        yield connection


def test_this_schema_has_nothing_to_report() -> None:
    assert findings() == []


def test_the_check_exits_clean(capsys: pytest.CaptureFixture[str]) -> None:
    assert main() == 0
    assert "check_indexes" in capsys.readouterr().out


def test_the_tables_come_back_by_name(open_book: sqlite3.Connection) -> None:
    found = tables(open_book)
    assert "reach" in found
    assert "trip" in found
    assert not any(name.startswith("sqlite_") for name in found)


def test_the_foreign_keys_of_a_table_come_back(open_book: sqlite3.Connection) -> None:
    assert set(foreign_keys(open_book, "trip")) == {"scow", "reach", "placement"}


def test_a_table_with_no_foreign_key_has_none(open_book: sqlite3.Connection) -> None:
    assert foreign_keys(open_book, "reach") == []


def test_a_primary_key_counts_as_indexed(open_book: sqlite3.Connection) -> None:
    assert "ident" in indexed(open_book, "reach")


def test_the_leading_column_of_an_index_counts(open_book: sqlite3.Connection) -> None:
    assert "scow" in indexed(open_book, "trip")
    assert "placement" in indexed(open_book, "trip")


def test_a_bare_foreign_key_is_found(open_book: sqlite3.Connection) -> None:
    open_book.execute("CREATE TABLE parent (ident TEXT PRIMARY KEY)")
    open_book.execute(
        "CREATE TABLE child (ident TEXT PRIMARY KEY,"
        " parent TEXT NOT NULL REFERENCES parent (ident))"
    )
    found = findings(open_book)
    assert found == ["child.parent is a foreign key with no index behind it"]


def test_an_index_takes_the_finding_away(open_book: sqlite3.Connection) -> None:
    open_book.execute("CREATE TABLE parent (ident TEXT PRIMARY KEY)")
    open_book.execute(
        "CREATE TABLE child (ident TEXT PRIMARY KEY,"
        " parent TEXT NOT NULL REFERENCES parent (ident))"
    )
    open_book.execute("CREATE INDEX child_by_parent ON child (parent)")
    assert findings(open_book) == []


def test_an_index_that_does_not_lead_with_the_key_does_not_count(
    open_book: sqlite3.Connection,
) -> None:
    open_book.execute("CREATE TABLE parent (ident TEXT PRIMARY KEY)")
    open_book.execute(
        "CREATE TABLE child (ident TEXT PRIMARY KEY, made TEXT NOT NULL,"
        " parent TEXT NOT NULL REFERENCES parent (ident))"
    )
    open_book.execute("CREATE INDEX child_by_made ON child (made, parent)")
    assert findings(open_book) != []
