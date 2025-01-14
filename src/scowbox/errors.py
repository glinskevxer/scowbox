"""The exception hierarchy.

Every error this package raises carries a short stable code. The code is what
reports and the command line key off; the message is for whoever is reading.
Nothing here formats for a terminal and nothing here catches.
"""

from __future__ import annotations


class ScowboxError(Exception):
    """Base of every error raised by this package.

    Subclasses set ``code`` to a short kebab-case string. Two errors with the
    same code mean the same thing to a caller even when their messages differ.
    """

    code = "scowbox"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message


class InputError(ScowboxError):
    """A value handed in from outside does not have the shape it must have."""

    code = "input"


class FieldError(InputError):
    """A named field of a record is wrong, and the field is worth naming."""

    code = "field"

    def __init__(self, field: str, message: str) -> None:
        super().__init__(f"{field}: {message}")
        self.field = field


class RangeError(FieldError):
    """A numeric field sits outside the range the domain allows."""

    code = "range"

    def __init__(self, field: str, value: float, low: float, high: float) -> None:
        super().__init__(field, f"{value:g} is outside {low:g}..{high:g}")
        self.value = value
        self.low = low
        self.high = high


class MissingError(ScowboxError):
    """A record was looked up by identifier and is not there."""

    code = "missing"

    def __init__(self, kind: str, ident: str) -> None:
        super().__init__(f"no {kind} {ident}")
        self.kind = kind
        self.ident = ident


class DuplicateError(ScowboxError):
    """A record was added under an identifier that is already taken."""

    code = "duplicate"

    def __init__(self, kind: str, ident: str) -> None:
        super().__init__(f"{kind} {ident} already exists")
        self.kind = kind
        self.ident = ident


class StateError(ScowboxError):
    """The operation is well formed but the record is in the wrong state."""

    code = "state"


class RuleError(ScowboxError):
    """A contract or regulatory rule forbids what was asked for."""

    code = "rule"


def code_of(error: BaseException) -> str:
    """Return the stable code for ``error``, or ``unknown`` for a stranger."""
    if isinstance(error, ScowboxError):
        return error.code
    return "unknown"
