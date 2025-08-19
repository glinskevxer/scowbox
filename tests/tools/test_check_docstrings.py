"""The docstring check, on this package and on something broken."""

from __future__ import annotations

from pathlib import Path

import pytest

from scowbox.tools.check_docstrings import findings, main
from scowbox.tools.scan import parse


def a_module(tmp_path: Path, text: str) -> list[str]:
    where = tmp_path / "sample.py"
    where.write_text(text, encoding="utf-8")
    return findings([parse(where, tmp_path)])


def test_this_package_passes() -> None:
    assert findings() == []


def test_the_check_exits_clean(capsys: pytest.CaptureFixture[str]) -> None:
    assert main() == 0
    assert "check_docstrings" in capsys.readouterr().out


def test_a_module_with_no_docstring_is_found(tmp_path: Path) -> None:
    found = a_module(tmp_path, "x = 1\n")
    assert found == ["scowbox.sample has no module docstring"]


def test_a_one_word_module_docstring_is_too_thin(tmp_path: Path) -> None:
    found = a_module(tmp_path, '"""Stuff."""\n')
    assert "under 4 words" in found[0]


def test_a_public_function_with_no_docstring_is_found(tmp_path: Path) -> None:
    found = a_module(
        tmp_path, '"""A sample module for the check."""\n\n\ndef go() -> None:\n    pass\n'
    )
    assert found == ["scowbox.sample.go has no docstring"]


def test_a_private_function_is_exempt(tmp_path: Path) -> None:
    found = a_module(
        tmp_path, '"""A sample module for the check."""\n\n\ndef _go() -> None:\n    pass\n'
    )
    assert found == []


def test_a_class_with_no_docstring_is_found(tmp_path: Path) -> None:
    found = a_module(tmp_path, '"""A sample module for the check."""\n\n\nclass Thing:\n    pass\n')
    assert found == ["scowbox.sample.Thing has no docstring"]


def test_a_clean_module_reports_nothing(tmp_path: Path) -> None:
    found = a_module(
        tmp_path,
        '"""A sample module for the check."""\n\n\n'
        'def go() -> None:\n    """Go and do the thing."""\n',
    )
    assert found == []
