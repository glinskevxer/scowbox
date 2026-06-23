"""The size check, on this package and on something that has grown."""

from __future__ import annotations

from pathlib import Path

import pytest

from scowbox.tools.check_size import (
    FUNCTION_CEILING,
    MODULE_CEILING,
    findings,
    function_sizes,
    main,
    module_size,
)
from scowbox.tools.scan import Module, modules, parse


def a_module(tmp_path: Path, body: str) -> list[Module]:
    where = tmp_path / "job"
    where.mkdir(exist_ok=True)
    module = where / "sample.py"
    module.write_text('"""A sample module for the check."""\n' + body, encoding="utf-8")
    return [parse(module, tmp_path)]


def test_this_package_has_nothing_to_report() -> None:
    assert findings() == []


def test_the_check_exits_clean(capsys: pytest.CaptureFixture[str]) -> None:
    assert main() == 0
    assert "check_size" in capsys.readouterr().out


def test_the_ceilings_sit_above_the_largest_module_here() -> None:
    assert max(module_size(m) for m in modules()) < MODULE_CEILING
    assert (
        max((size for m in modules() for _, size in function_sizes(m)), default=0)
        < FUNCTION_CEILING
    )


def test_a_docstring_costs_nothing(tmp_path: Path) -> None:
    plain = a_module(tmp_path, "x = 1\n")[0]
    padded = a_module(tmp_path, '"""More words about it."""\nx = 1\n')[0]
    assert module_size(plain) == module_size(padded)


def test_a_function_is_measured_without_its_own_definition(tmp_path: Path) -> None:
    module = a_module(tmp_path, "def go() -> None:\n    x = 1\n    y = 2\n")[0]
    assert function_sizes(module) == [("go", 2)]


def test_a_nested_function_is_measured_too(tmp_path: Path) -> None:
    module = a_module(
        tmp_path,
        "def go() -> None:\n    def inner() -> None:\n        x = 1\n    inner()\n",
    )[0]
    assert dict(function_sizes(module))["inner"] == 1


def test_a_module_past_the_ceiling_is_found(tmp_path: Path) -> None:
    body = "\n".join(f"x{n} = {n}" for n in range(MODULE_CEILING + 1))
    found = findings(a_module(tmp_path, body + "\n"))
    assert "past the" in found[0]
    assert "scowbox.job.sample is" in found[0]


def test_a_function_past_the_ceiling_is_found(tmp_path: Path) -> None:
    body = "def go() -> None:\n" + "\n".join(f"    x{n} = {n}" for n in range(FUNCTION_CEILING + 1))
    found = findings(a_module(tmp_path, body + "\n"))
    assert any("sample.go is" in line for line in found)


def test_a_module_of_small_functions_is_left_alone(tmp_path: Path) -> None:
    body = "\n\n".join(f"def go{n}() -> None:\n    x = {n}" for n in range(10))
    assert findings(a_module(tmp_path, body + "\n")) == []
