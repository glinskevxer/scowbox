"""Findings, their ranking and their ordering."""

from __future__ import annotations

import datetime as dt

import pytest

from scowbox.compliance.findings import Finding, Severity, counted, ordered, worst
from scowbox.errors import FieldError

DAY = dt.date(2025, 6, 4)


def a_finding(
    subject: str = "SH-00021",
    severity: Severity = Severity.WARNING,
    day: dt.date = DAY,
    kind: str = "window",
) -> Finding:
    return Finding(kind, subject, day, severity, "something to look at")


def test_severity_ranks_in_the_order_the_words_do() -> None:
    assert Severity.VIOLATION.rank > Severity.WARNING.rank > Severity.NOTE.rank


def test_only_a_violation_is_reportable() -> None:
    assert Severity.VIOLATION.reportable
    assert not Severity.WARNING.reportable
    assert not Severity.NOTE.reportable


def test_a_finding_needs_a_kind_a_subject_and_a_detail() -> None:
    with pytest.raises(FieldError):
        Finding(" ", "SH-1", DAY, Severity.NOTE, "d")
    with pytest.raises(FieldError):
        Finding("window", " ", DAY, Severity.NOTE, "d")
    with pytest.raises(FieldError):
        Finding("window", "SH-1", DAY, Severity.NOTE, " ")


def test_a_finding_prints_as_one_line() -> None:
    line = a_finding().line()
    assert line.startswith("2025-06-04  warning   SH-00021")


def test_the_worst_comes_first() -> None:
    got = ordered([a_finding(severity=Severity.NOTE), a_finding(severity=Severity.VIOLATION)])
    assert got[0].severity is Severity.VIOLATION


def test_within_a_severity_the_oldest_comes_first() -> None:
    got = ordered(
        [
            a_finding(day=dt.date(2025, 6, 10)),
            a_finding(day=dt.date(2025, 6, 1)),
        ]
    )
    assert got[0].day == dt.date(2025, 6, 1)


def test_within_a_day_the_subject_orders() -> None:
    got = ordered([a_finding(subject="SH-00099"), a_finding(subject="SH-00021")])
    assert [f.subject for f in got] == ["SH-00021", "SH-00099"]


def test_the_worst_severity_is_reported() -> None:
    assert worst([a_finding(severity=Severity.NOTE), a_finding()]) is Severity.WARNING
    assert worst([]) is None


def test_findings_are_counted_by_severity() -> None:
    tally = counted([a_finding(), a_finding(severity=Severity.VIOLATION)])
    assert tally[Severity.WARNING] == 1
    assert tally[Severity.VIOLATION] == 1
    assert tally[Severity.NOTE] == 0
