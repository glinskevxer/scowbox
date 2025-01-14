"""The exception hierarchy carries codes, and the codes are what callers read."""

from __future__ import annotations

import pytest

from scowbox.errors import (
    DuplicateError,
    FieldError,
    InputError,
    MissingError,
    RangeError,
    RuleError,
    ScowboxError,
    StateError,
    code_of,
)


def test_every_error_is_a_scowbox_error() -> None:
    family: tuple[type[ScowboxError], ...] = (
        InputError,
        FieldError,
        RangeError,
        MissingError,
        DuplicateError,
        StateError,
        RuleError,
    )
    for cls in family:
        assert issubclass(cls, ScowboxError)


def test_codes_are_distinct_per_class() -> None:
    codes = [
        ScowboxError.code,
        InputError.code,
        FieldError.code,
        RangeError.code,
        MissingError.code,
        DuplicateError.code,
        StateError.code,
        RuleError.code,
    ]
    assert len(set(codes)) == len(codes)


def test_field_error_names_the_field() -> None:
    err = FieldError("bottom_width", "must be positive")
    assert err.field == "bottom_width"
    assert str(err) == "bottom_width: must be positive"


def test_range_error_reports_the_bounds_it_broke() -> None:
    err = RangeError("side_slope", 0.5, 1.0, 10.0)
    assert err.value == 0.5
    assert err.low == 1.0
    assert err.high == 10.0
    assert "0.5 is outside 1..10" in str(err)


def test_range_error_is_a_field_error() -> None:
    with pytest.raises(FieldError) as caught:
        raise RangeError("depth", 99.0, 0.0, 80.0)
    assert caught.value.field == "depth"


def test_missing_and_duplicate_read_as_sentences() -> None:
    assert str(MissingError("reach", "R-4")) == "no reach R-4"
    assert str(DuplicateError("scow", "SC-9")) == "scow SC-9 already exists"


def test_code_of_falls_back_for_a_stranger() -> None:
    assert code_of(RuleError("closed window")) == "rule"
    assert code_of(ValueError("not ours")) == "unknown"
