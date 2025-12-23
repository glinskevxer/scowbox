"""Reaching the book from a command.

``with book(ctx.obj["book"]) as connection`` was written out forty one times,
and the string key in the middle of it was a typo waiting to happen: a command
that reads ``ctx.obj["path"]`` raises a KeyError with no message, from inside a
context manager, on a machine that is not this one.

So the key is written once. Commands ask the context for a book and do not know
how it is stored.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

import click

from scowbox.store.book import book

BOOK = "book"


def book_path(ctx: click.Context) -> str:
    """Where the book this invocation is working on lives."""
    ctx.ensure_object(dict)
    return str(ctx.obj.get(BOOK, "scowbox.sqlite3"))


@contextmanager
def opened(ctx: click.Context, *, create: bool = False) -> Iterator[sqlite3.Connection]:
    """Open the book named on the command line, and close it afterwards."""
    with book(book_path(ctx), create=create) as connection:
        yield connection
