"""The pin check, on this project and on a range."""

from __future__ import annotations

import pytest

from scowbox.tools.check_pins import (
    constrained,
    constraints_text,
    declared,
    findings,
    lock_paths,
    main,
    pyproject_text,
)


def test_this_project_has_nothing_to_report() -> None:
    assert findings() == []


def test_the_check_exits_clean(capsys: pytest.CaptureFixture[str]) -> None:
    assert main() == 0
    assert "check_pins" in capsys.readouterr().out


def test_both_files_are_in_the_checkout() -> None:
    assert all(path.exists() for path in lock_paths())


def test_the_direct_dependencies_are_found() -> None:
    names = [name for name, _ in declared(pyproject_text())]
    assert "click" in names
    assert "pytest" in names
    assert "ruff" in names


def test_the_closure_is_read_off_the_constraints() -> None:
    pins = constrained(constraints_text())
    assert pins["click"] == "8.1.8"
    assert "pluggy" in pins


def test_comments_in_the_constraints_are_skipped() -> None:
    assert constrained("# click==1.0\nclick==8.1.8\n") == {"click": "8.1.8"}


def test_an_underscore_and_a_dash_are_the_same_package() -> None:
    assert constrained("mypy_extensions==1.0.0\n") == {"mypy-extensions": "1.0.0"}


def test_a_range_is_found() -> None:
    project = 'dependencies = [\n  "click>=8.1",\n]\n'
    found = findings(project, "click==8.1.8\n")
    assert "not an exact pin" in found[0]


def test_a_pin_missing_from_the_constraints_is_found() -> None:
    project = 'dependencies = [\n  "click==8.1.8",\n]\n'
    found = findings(project, "pytest==8.3.4\n")
    assert "missing from constraints.txt" in found[0]


def test_two_files_disagreeing_is_found() -> None:
    project = 'dependencies = [\n  "click==8.1.8",\n]\n'
    found = findings(project, "click==8.2.0\n")
    assert "8.1.8 in pyproject.toml and 8.2.0 in constraints.txt" in found[0]


def test_the_optional_dependencies_are_checked_too() -> None:
    project = 'dev = [\n  "ruff==0.9.2",\n]\n'
    assert findings(project, "ruff==0.9.2\n") == []
    assert findings(project, "ruff==0.9.3\n") != []
