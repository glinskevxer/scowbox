"""What a sweep finds."""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

from scowbox.errors import FieldError


class Severity(Enum):
    """How much a finding matters."""

    NOTE = "note"
    WARNING = "warning"
    VIOLATION = "violation"

    @property
    def rank(self) -> int:
        return {Severity.NOTE: 0, Severity.WARNING: 1, Severity.VIOLATION: 2}[self]

    @property
    def reportable(self) -> bool:
        """True when the finding goes to the owner rather than into the file."""
        return self is Severity.VIOLATION


@dataclass(frozen=True)
class Finding:
    """One disagreement between a record and a rule."""

    kind: str
    subject: str
    day: dt.date
    severity: Severity
    detail: str

    def __post_init__(self) -> None:
        if not self.kind.strip():
            raise FieldError("kind", "a finding says what kind it is")
        if not self.subject.strip():
            raise FieldError("subject", "a finding names what it is about")
        if not self.detail.strip():
            raise FieldError("detail", "a finding says what is wrong")

    def line(self) -> str:
        return f"{self.day}  {self.severity.value:<9} {self.subject:<10} {self.detail}"


def ordered(findings: Iterable[Finding]) -> tuple[Finding, ...]:
    """Worst first, then oldest, then by subject."""
    return tuple(sorted(findings, key=lambda f: (-f.severity.rank, f.day, f.subject, f.kind)))


def worst(findings: Iterable[Finding]) -> Severity | None:
    """The severity of the worst finding, or nothing when there are none."""
    ranked = [f.severity for f in findings]
    if not ranked:
        return None
    return max(ranked, key=lambda s: s.rank)


def counted(findings: Iterable[Finding]) -> dict[Severity, int]:
    """How many findings of each severity."""
    tally = dict.fromkeys(Severity, 0)
    for finding in findings:
        tally[finding.severity] += 1
    return tally
