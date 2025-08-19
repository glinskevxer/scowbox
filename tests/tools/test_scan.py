"""The source scanner every check is built on."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from scowbox.tools.scan import (
    module_name,
    modules,
    package_root,
    parse,
    project_root,
    report,
    source_files,
    suite_files,
)


def test_the_package_root_holds_the_package() -> None:
    assert (package_root() / "errors.py").exists()


def test_the_project_root_holds_the_pyproject() -> None:
    assert (project_root() / "pyproject.toml").exists()


def test_every_source_file_is_a_module() -> None:
    found = source_files()
    assert len(found) > 30
    assert all(p.suffix == ".py" for p in found)
    assert not any("__pycache__" in p.parts for p in found)


def test_source_files_come_back_in_a_stable_order() -> None:
    assert source_files() == sorted(source_files())


def test_the_tests_are_found_too() -> None:
    found = suite_files()
    assert len(found) > 20
    assert all(p.name.startswith("test_") for p in found)


def test_a_module_name_is_dotted_from_the_package() -> None:
    assert module_name(package_root() / "errors.py") == "scowbox.errors"
    assert module_name(package_root() / "units" / "money.py") == "scowbox.units.money"


def test_a_package_init_takes_the_package_name() -> None:
    assert module_name(package_root() / "units" / "__init__.py") == "scowbox.units"


def test_a_parsed_module_carries_its_tree(tmp_path: Path) -> None:
    where = tmp_path / "sample.py"
    where.write_text('"""A sample."""\n\n\ndef go() -> None:\n    """Go."""\n', encoding="utf-8")
    module = parse(where, tmp_path)
    assert module.name == "scowbox.sample"
    assert [f.name for f in module.functions()] == ["go"]
    assert ast.get_docstring(module.tree) == "A sample."


def test_classes_and_imports_come_back(tmp_path: Path) -> None:
    where = tmp_path / "sample.py"
    where.write_text(
        '"""A sample."""\n'
        "from scowbox.errors import RuleError\n"
        "import scowbox.ids\n"
        "import json\n\n\n"
        "class Thing:\n"
        '    """A thing."""\n',
        encoding="utf-8",
    )
    module = parse(where, tmp_path)
    assert [c.name for c in module.classes()] == ["Thing"]
    assert sorted(module.imports()) == ["scowbox.errors", "scowbox.ids"]


def test_every_module_of_the_package_parses() -> None:
    assert len(modules()) == len(source_files())


def test_a_clean_report_returns_zero(capsys: pytest.CaptureFixture[str]) -> None:
    assert report("check_sample", []) == 0
    assert "nothing to report" in capsys.readouterr().out


def test_a_report_with_findings_returns_one(capsys: pytest.CaptureFixture[str]) -> None:
    assert report("check_sample", ["a", "b"]) == 1
    out = capsys.readouterr().out
    assert "2 findings" in out
    assert "  a" in out
