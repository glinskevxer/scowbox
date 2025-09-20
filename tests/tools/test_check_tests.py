"""The suite reach check."""

from __future__ import annotations

import pytest

from scowbox.tools.check_tests import (
    findings,
    has_own_suite,
    imported_by_suite,
    main,
    suite_file_for,
)
from scowbox.tools.scan import modules


def test_this_package_passes() -> None:
    assert findings() == []


def test_the_check_exits_clean(capsys: pytest.CaptureFixture[str]) -> None:
    assert main() == 0
    assert "check_tests" in capsys.readouterr().out


def test_the_suite_names_a_lot_of_modules() -> None:
    assert len(imported_by_suite()) > 30


def test_a_module_the_suite_never_names_is_found() -> None:
    found = findings({"scowbox.errors"})
    assert any("scowbox.model.plant" in line for line in found)
    assert all("has no test" in line for line in found)


def test_a_module_the_suite_names_is_not_found() -> None:
    assert not any("scowbox.errors" in line for line in findings({"scowbox.errors"}))


def test_a_module_with_a_mirrored_test_file_passes_without_being_named() -> None:
    found = findings({"scowbox.errors"})
    assert not any("scowbox.units.money" in line for line in found)
    assert not any("scowbox.cli.reach" in line for line in found)


def test_the_expected_test_file_mirrors_the_module_path() -> None:
    money = next(m for m in modules() if m.name == "scowbox.units.money")
    assert suite_file_for(money) == "tests/units/test_money.py"
    assert has_own_suite(money)
