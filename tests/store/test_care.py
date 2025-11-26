"""The book's own health, its copies and its size."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.errors import StateError
from scowbox.model.channel import Method, Reach, Template
from scowbox.store import reaches
from scowbox.store.book import book
from scowbox.store.care import backup, compact, health
from scowbox.store.migrations import latest
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline


@pytest.fixture
def open_book(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with book(tmp_path / "book.sqlite3", create=True) as connection:
        yield connection


def a_reach(ident: str = "RCH-012") -> Reach:
    return Reach(
        ident=ident,
        name="Lower Range",
        line=Reachline.parse("100+00", "140+00"),
        template=Template(bottom_width=400, authorized_depth=Depth.of_feet(42), side_slope=3),
        method=Method.SURVEY,
        group="base",
    )


def test_a_fresh_book_is_sound(open_book: sqlite3.Connection) -> None:
    found = health(open_book)
    assert found.sound
    assert found.integrity == "ok"
    assert found.orphans == ()


def test_the_version_is_the_latest_migration(open_book: sqlite3.Connection) -> None:
    assert health(open_book).version == latest()


def test_a_book_from_an_older_version_is_not_sound(open_book: sqlite3.Connection) -> None:
    open_book.execute("PRAGMA user_version = 1")
    assert not health(open_book).sound


def test_the_tables_are_counted(open_book: sqlite3.Connection) -> None:
    assert health(open_book).tables > 8


def test_the_size_is_pages_by_page_size(open_book: sqlite3.Connection) -> None:
    found = health(open_book)
    assert found.bytes_used == found.pages * found.page_size
    assert found.bytes_used > 0


def test_an_orphan_row_is_found(open_book: sqlite3.Connection) -> None:
    open_book.execute("PRAGMA foreign_keys = OFF")
    open_book.execute(
        "INSERT INTO survey (ident, reach, kind, taken_on, vessel, transducer_draft, gauge)"
        " VALUES ('SV-0031', 'RCH-999', 'before', '2025-03-14', 'Cape Fear', 2.5, '')"
    )
    found = health(open_book)
    assert found.orphans
    assert not found.sound


def test_a_backup_is_a_book_of_its_own(open_book: sqlite3.Connection, tmp_path: Path) -> None:
    reaches.add(open_book, a_reach())
    made = backup(open_book, tmp_path / "copy.sqlite3")
    with book(made) as copy:
        assert reaches.get(copy, "RCH-012") == a_reach()


def test_a_backup_does_not_overwrite(open_book: sqlite3.Connection, tmp_path: Path) -> None:
    where = tmp_path / "copy.sqlite3"
    backup(open_book, where)
    with pytest.raises(StateError):
        backup(open_book, where)


def test_a_backup_makes_the_directory_it_needs(
    open_book: sqlite3.Connection, tmp_path: Path
) -> None:
    made = backup(open_book, tmp_path / "elsewhere" / "copy.sqlite3")
    assert made.exists()


def test_compacting_gives_bytes_back(
    open_book: sqlite3.Connection,
) -> None:
    for number in range(200):
        reaches.add(open_book, a_reach(f"RCH-{number + 1:03d}"))
    for number in range(200):
        reaches.remove(open_book, f"RCH-{number + 1:03d}")
    assert compact(open_book) > 0


def test_compacting_an_almost_empty_book_moves_at_most_a_page(
    open_book: sqlite3.Connection,
) -> None:
    given = compact(open_book)
    assert abs(given) <= health(open_book).page_size
