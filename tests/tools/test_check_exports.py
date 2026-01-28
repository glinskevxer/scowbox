"""The export check, on this package and on a name nothing calls."""

from __future__ import annotations

from pathlib import Path

import pytest

from scowbox.tools.check_exports import defined, findings, main, used
from scowbox.tools.scan import Module, parse


def a_module(tmp_path: Path, body: str, name: str = "sample") -> list[Module]:
    where = tmp_path / "job"
    where.mkdir(exist_ok=True)
    module = where / f"{name}.py"
    module.write_text('"""A sample module for the check."""\n' + body, encoding="utf-8")
    return [parse(module, tmp_path)]


def test_this_package_has_nothing_to_report() -> None:
    assert findings() == []


def test_the_check_exits_clean(capsys: pytest.CaptureFixture[str]) -> None:
    assert main() == 0
    assert "check_exports" in capsys.readouterr().out


def test_public_names_are_found(tmp_path: Path) -> None:
    module = a_module(tmp_path, "def go() -> None:\n    pass\n\n\nclass Thing:\n    pass\n")[0]
    assert defined(module) == ["go", "Thing"]


def test_a_private_name_is_not_an_export(tmp_path: Path) -> None:
    module = a_module(tmp_path, "def _go() -> None:\n    pass\n")[0]
    assert defined(module) == []


def test_a_decorated_name_is_not_an_export(tmp_path: Path) -> None:
    module = a_module(
        tmp_path, "import click\n\n\n@click.command()\ndef go() -> None:\n    pass\n"
    )[0]
    assert defined(module) == []


def test_a_name_nothing_calls_is_found(tmp_path: Path) -> None:
    found = findings(a_module(tmp_path, "def unreachable_helper() -> None:\n    pass\n"))
    assert found == ["scowbox.job.sample.unreachable_helper is used nowhere else"]


def test_a_name_another_module_calls_is_left_alone(tmp_path: Path) -> None:
    modules = [
        *a_module(tmp_path, "def shared_helper() -> None:\n    pass\n", "one"),
        *a_module(
            tmp_path,
            "from scowbox.job.one import shared_helper\n\n\n"
            "def other() -> None:\n    shared_helper()\n",
            "two",
        ),
    ]
    assert "shared_helper" not in " ".join(findings(modules))


def test_main_and_run_are_always_taken_as_used(tmp_path: Path) -> None:
    found = findings(a_module(tmp_path, "def main() -> int:\n    return 0\n"))
    assert found == []


def test_the_uses_come_back_keyed_by_name() -> None:
    where = used()
    assert "measure" in where
    assert len(where["measure"]) > 1
