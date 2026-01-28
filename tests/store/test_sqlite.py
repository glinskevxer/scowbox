"""Connections close, transactions roll back, and queries clean up after."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from scowbox.errors import FieldError, StateError
from scowbox.store.sqlite import (
    configure,
    one,
    opened,
    rows,
    sql_identifier,
    sql_integer,
    written,
)


def test_a_connection_is_closed_on_the_way_out(tmp_path: Path) -> None:
    with opened(tmp_path / "book.sqlite3") as connection:
        connection.execute("CREATE TABLE t (a INTEGER)")
    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")


def test_a_connection_is_closed_even_when_the_body_raises(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError), opened(tmp_path / "book.sqlite3") as connection:
        raise RuntimeError("something in the middle")
    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")


def test_foreign_keys_are_on(tmp_path: Path) -> None:
    with opened(tmp_path / "book.sqlite3") as connection:
        assert one(connection, "PRAGMA foreign_keys")[0] == 1


def test_rows_come_back_by_column_name(tmp_path: Path) -> None:
    with opened(tmp_path / "book.sqlite3") as connection:
        connection.execute("CREATE TABLE t (a INTEGER, b TEXT)")
        connection.execute("INSERT INTO t VALUES (1, 'one')")
        assert one(connection, "SELECT a, b FROM t")["b"] == "one"


def test_expecting_one_row_and_finding_none_says_so(tmp_path: Path) -> None:
    with opened(tmp_path / "book.sqlite3") as connection:
        connection.execute("CREATE TABLE t (a INTEGER)")
        with pytest.raises(StateError):
            one(connection, "SELECT a FROM t")


def test_rows_returns_every_row_of_a_query(tmp_path: Path) -> None:
    with opened(tmp_path / "book.sqlite3") as connection:
        connection.execute("CREATE TABLE t (a INTEGER)")
        connection.executemany("INSERT INTO t VALUES (?)", [(1,), (2,), (3,)])
        assert [r["a"] for r in rows(connection, "SELECT a FROM t ORDER BY a")] == [1, 2, 3]


def test_a_written_block_commits_on_the_way_out(tmp_path: Path) -> None:
    with opened(tmp_path / "book.sqlite3") as connection:
        connection.execute("CREATE TABLE t (a INTEGER)")
        with written(connection):
            connection.execute("INSERT INTO t VALUES (1)")
        assert len(rows(connection, "SELECT a FROM t")) == 1


def insert_then_fail(connection: sqlite3.Connection) -> None:
    with written(connection):
        connection.execute("INSERT INTO t VALUES (1)")
        raise RuntimeError("half way through")


def test_a_written_block_rolls_back_on_an_error(tmp_path: Path) -> None:
    with opened(tmp_path / "book.sqlite3") as connection:
        connection.execute("CREATE TABLE t (a INTEGER)")
        with pytest.raises(RuntimeError):
            insert_then_fail(connection)
        assert rows(connection, "SELECT a FROM t") == []


def test_a_plain_identifier_passes_through() -> None:
    assert sql_identifier("reach") == "reach"
    assert sql_identifier("line_item") == "line_item"


@pytest.mark.parametrize("name", ["", "reach; drop table x", "1reach", "reach reach", "*"])
def test_anything_but_a_plain_identifier_is_refused(name: str) -> None:
    with pytest.raises(FieldError):
        sql_identifier(name)


def test_a_whole_number_passes_through() -> None:
    assert sql_integer(9) == "9"
    assert sql_integer(0) == "0"


@pytest.mark.parametrize("value", ["9", 9.5, None, True])
def test_anything_but_a_whole_number_is_refused(value: object) -> None:
    with pytest.raises(FieldError):
        sql_integer(value)


def test_configure_sets_the_pragmas_and_the_row_factory(tmp_path: Path) -> None:
    connection = sqlite3.connect(str(tmp_path / "raw.sqlite3"))
    try:
        assert configure(connection) is connection
        assert connection.row_factory is sqlite3.Row
        assert one(connection, "PRAGMA foreign_keys")[0] == 1
    finally:
        connection.close()
