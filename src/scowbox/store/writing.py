"""Turning sqlite's integrity errors into this package's errors.

Six repositories were each catching ``IntegrityError`` and deciding, from the
text of the message, whether it meant a duplicate key or a foreign key that
does not point at anything. Six copies of that is six chances to get the test
backwards, and two of them already read the foreign key case as a duplicate.

So it lives here once. The caller says what kind of record it is writing and,
where the table has references, what a broken one would mean.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from scowbox.errors import DuplicateError, MissingError

FOREIGN_KEY = "FOREIGN KEY"


@contextmanager
def inserting(kind: str, ident: str, references: str = "") -> Iterator[None]:
    """Run an insert, naming what a constraint failure would mean.

    ``kind`` is what is being written, for the duplicate message. ``references``
    is what a foreign key failure points at, for the missing message; leave it
    out on a table with no references and any integrity failure reads as a
    duplicate.
    """
    try:
        yield
    except sqlite3.IntegrityError as error:
        if references and FOREIGN_KEY in str(error):
            raise MissingError(references, ident) from None
        raise DuplicateError(kind, ident) from None
