"""Commands reach the book through one place."""

from __future__ import annotations

from pathlib import Path

import click
import pytest

from scowbox.cli.context import BOOK, book_path, opened
from scowbox.errors import MissingError
from scowbox.store.migrations import latest, version_of


def a_context(**obj: object) -> click.Context:
    return click.Context(click.Command("sample"), obj=dict(obj))


def test_the_path_comes_out_of_the_context() -> None:
    assert book_path(a_context(book="/tmp/other.sqlite3")) == "/tmp/other.sqlite3"


def test_a_context_with_nothing_in_it_takes_the_default() -> None:
    assert book_path(a_context()) == "scowbox.sqlite3"


def test_the_key_is_the_one_the_group_writes() -> None:
    assert BOOK == "book"


def test_a_book_opens_migrated(tmp_path: Path) -> None:
    ctx = a_context(book=str(tmp_path / "book.sqlite3"))
    with opened(ctx, create=True) as connection:
        assert version_of(connection) == latest()


def test_a_book_that_is_not_there_is_not_created_by_accident(tmp_path: Path) -> None:
    ctx = a_context(book=str(tmp_path / "nothing.sqlite3"))
    with pytest.raises(MissingError), opened(ctx):
        pass


def test_the_connection_closes_behind_the_block(tmp_path: Path) -> None:
    ctx = a_context(book=str(tmp_path / "book.sqlite3"))
    with opened(ctx, create=True) as connection:
        pass
    with pytest.raises(Exception, match="closed"):
        connection.execute("SELECT 1")
