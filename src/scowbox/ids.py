"""Record identifiers.

Every record in the book is named by a prefix and a zero padded number: reach
``RCH-012``, survey ``SV-0031``, scow trip ``TR-04188``. The prefix is not
decoration. A pay estimate names quantities that came from a survey and from a
set of scow trips, and a reader with the identifier alone has to know which of
the two they are holding.

Numbers are allocated by the store, not here. This module knows the shapes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from scowbox.errors import FieldError, MissingError


@dataclass(frozen=True)
class IdentKind:
    """The shape of one family of identifiers."""

    name: str
    prefix: str
    width: int

    @property
    def pattern(self) -> re.Pattern[str]:
        return re.compile(rf"^{self.prefix}-([0-9]{{{self.width}}})$")

    @property
    def ceiling(self) -> int:
        """One past the largest number this shape can hold."""
        return int(10**self.width)


KINDS: tuple[IdentKind, ...] = (
    IdentKind("reach", "RCH", 3),
    IdentKind("survey", "SV", 4),
    IdentKind("scow", "SC", 3),
    IdentKind("trip", "TR", 5),
    IdentKind("placement", "PA", 3),
    IdentKind("plant", "DR", 3),
    IdentKind("shift", "SH", 5),
    IdentKind("item", "LI", 4),
    IdentKind("estimate", "EST", 3),
)

_BY_NAME = {k.name: k for k in KINDS}
_BY_PREFIX = {k.prefix: k for k in KINDS}


def kind(name: str) -> IdentKind:
    """Look up an identifier shape by the record name it belongs to."""
    try:
        return _BY_NAME[name]
    except KeyError:
        raise MissingError("identifier kind", name) from None


def format_ident(name: str, number: int) -> str:
    """Render ``number`` as an identifier of the named kind."""
    shape = kind(name)
    if number < 1 or number >= shape.ceiling:
        raise FieldError(name, f"number {number} does not fit {shape.prefix}-{'0' * shape.width}")
    return f"{shape.prefix}-{number:0{shape.width}d}"


def parse_ident(name: str, text: str) -> int:
    """Read the number out of an identifier, checking it is of the named kind."""
    shape = kind(name)
    match = shape.pattern.match(text)
    if match is None:
        raise FieldError(name, f"{text!r} is not a {shape.prefix} identifier")
    return int(match.group(1))


def is_ident(name: str, text: str) -> bool:
    """True when ``text`` is a well formed identifier of the named kind."""
    return kind(name).pattern.match(text) is not None


def kind_of(text: str) -> IdentKind:
    """Work out which family an identifier belongs to from its prefix."""
    head, _, _ = text.partition("-")
    shape = _BY_PREFIX.get(head)
    if shape is None or shape.pattern.match(text) is None:
        raise FieldError("identifier", f"{text!r} is not an identifier this book issues")
    return shape


def sort_key(text: str) -> tuple[str, int]:
    """Order identifiers by family then by number, not by their text.

    ``TR-00099`` sorts before ``TR-00100`` here and after it as a string, which
    is the whole reason this exists.
    """
    shape = kind_of(text)
    return (shape.prefix, parse_ident(shape.name, text))
