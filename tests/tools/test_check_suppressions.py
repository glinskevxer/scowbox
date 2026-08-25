"""The suppression check, on the package it guards."""

from __future__ import annotations

import re

import pytest

from scowbox.tools.check_suppressions import MARKS, findings, main


def test_this_package_has_nothing_to_report() -> None:
    assert findings() == []


def test_the_check_exits_clean(capsys: pytest.CaptureFixture[str]) -> None:
    assert main() == 0
    assert "check_suppressions" in capsys.readouterr().out


def matched(line: str) -> bool:
    return any(mark.search(line) for mark in MARKS)


def test_a_lint_suppression_is_matched() -> None:
    assert matched("x = 1  # noqa: BLE001")
    assert matched("x = 1  # noqa")


def test_a_type_suppression_is_matched() -> None:
    assert matched("x = f()  # type: ignore[arg-type]")
    assert matched("x = f()  #type:ignore")


def test_a_coverage_suppression_is_matched() -> None:
    assert matched("if False:  # pragma: no cover")


def test_ordinary_code_is_not_matched() -> None:
    assert not matched("x = 1  # the tide is above datum here")
    assert not matched("return round(value, 2)")


def test_the_marks_are_patterns_not_plain_strings() -> None:
    assert all(isinstance(mark, re.Pattern) for mark in MARKS)


def test_a_mypy_file_level_suppression_is_matched() -> None:
    assert matched("# mypy: ignore-errors")


def test_every_mark_is_tried_against_a_line() -> None:
    assert len(MARKS) == 4


def test_a_suppression_anywhere_on_the_line_is_matched() -> None:
    assert matched("    return x  # noqa: E501  and a note after it")


def test_a_word_that_only_looks_like_one_is_not_matched() -> None:
    assert not matched("# the noqa convention is described in the readme")
    assert not matched("x = 1  # type of the value")


def test_the_findings_name_the_file_and_the_line() -> None:
    assert findings() == []
