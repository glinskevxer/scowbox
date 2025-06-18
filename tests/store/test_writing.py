"""The one place an integrity error is read."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.errors import DuplicateError, MissingError
from scowbox.store.book import book
from scowbox.store.writing import inserting


@pytest.fixture
def open_book(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with book(tmp_path / "book.sqlite3", create=True) as connection:
        connection.execute("CREATE TABLE parent (ident TEXT PRIMARY KEY)")
        connection.execute(
            "CREATE TABLE child ("
            " ident TEXT PRIMARY KEY,"
            " parent TEXT NOT NULL REFERENCES parent (ident))"
        )
        connection.execute("INSERT INTO parent VALUES ('P-1')")
        yield connection


def test_a_clean_insert_passes_through(open_book: sqlite3.Connection) -> None:
    with inserting("child", "C-1", references="parent"):
        open_book.execute("INSERT INTO child VALUES ('C-1', 'P-1')")
    assert open_book.execute("SELECT count(*) FROM child").fetchone()[0] == 1


def test_a_repeated_key_reads_as_a_duplicate(open_book: sqlite3.Connection) -> None:
    open_book.execute("INSERT INTO child VALUES ('C-1', 'P-1')")
    with pytest.raises(DuplicateError) as caught, inserting("child", "C-1", references="parent"):
        open_book.execute("INSERT INTO child VALUES ('C-1', 'P-1')")
    assert caught.value.kind == "child"


def test_a_broken_reference_reads_as_missing(open_book: sqlite3.Connection) -> None:
    with pytest.raises(MissingError) as caught, inserting("child", "C-2", references="parent"):
        open_book.execute("INSERT INTO child VALUES ('C-2', 'P-9')")
    assert caught.value.kind == "parent"
    assert caught.value.ident == "C-2"


def test_without_a_reference_everything_reads_as_a_duplicate(
    open_book: sqlite3.Connection,
) -> None:
    with pytest.raises(DuplicateError), inserting("child", "C-2"):
        open_book.execute("INSERT INTO child VALUES ('C-2', 'P-9')")


def test_an_error_that_is_not_an_integrity_error_is_left_alone(
    open_book: sqlite3.Connection,
) -> None:
    with pytest.raises(sqlite3.OperationalError), inserting("child", "C-3"):
        open_book.execute("INSERT INTO nothing VALUES ('C-3')")
