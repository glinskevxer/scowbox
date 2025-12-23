"""The layer check, on this package and on an import that points up."""

from __future__ import annotations

from pathlib import Path

import pytest

from scowbox.tools.check_layers import LAYERS, findings, layer_of, main, unplaced
from scowbox.tools.scan import parse


def a_module(tmp_path: Path, text: str, name: str = "measure") -> list[str]:
    where = tmp_path / name
    where.mkdir(exist_ok=True)
    module = where / "sample.py"
    module.write_text(text, encoding="utf-8")
    return findings([parse(module, tmp_path)])


def test_this_package_has_nothing_to_report() -> None:
    assert findings() == []


def test_every_module_is_in_a_layer() -> None:
    assert unplaced() == []


def test_the_check_exits_clean(capsys: pytest.CaptureFixture[str]) -> None:
    assert main() == 0
    assert "check_layers" in capsys.readouterr().out


def test_the_layers_name_each_package_once() -> None:
    names = [name for layer in LAYERS for name in layer]
    assert len(set(names)) == len(names)


def test_a_layer_is_found_from_the_dotted_name() -> None:
    assert layer_of("scowbox.units.money") == 1
    assert layer_of("scowbox.cli.main") == 10
    assert layer_of("scowbox.errors") == 0


def test_the_package_root_is_in_no_layer() -> None:
    assert layer_of("scowbox") is None


def test_an_import_from_below_is_fine(tmp_path: Path) -> None:
    found = a_module(
        tmp_path, '"""A sample module for the check."""\nfrom scowbox.model.scow import Scow\n'
    )
    assert found == []


def test_an_import_from_the_same_layer_is_fine(tmp_path: Path) -> None:
    found = a_module(
        tmp_path, '"""A sample module for the check."""\nfrom scowbox.pay.estimate import build\n'
    )
    assert found == []


def test_an_import_from_above_is_found(tmp_path: Path) -> None:
    found = a_module(
        tmp_path,
        '"""A sample module for the check."""\nfrom scowbox.store.book import book\n',
    )
    assert found == ["scowbox.measure.sample (layer 4) imports scowbox.store.book (layer 6)"]


def test_a_rule_reaching_for_the_command_line_is_found(tmp_path: Path) -> None:
    found = a_module(tmp_path, '"""A sample module for the check."""\nimport scowbox.cli.main\n')
    assert "imports scowbox.cli.main" in found[0]


def test_a_module_in_no_layer_is_reported(tmp_path: Path) -> None:
    where = tmp_path / "invented"
    where.mkdir()
    module = where / "sample.py"
    module.write_text('"""A sample module for the check."""\n', encoding="utf-8")
    assert unplaced([parse(module, tmp_path)]) == [
        "scowbox.invented.sample is in no declared layer"
    ]


def test_an_import_of_something_outside_the_package_is_ignored(tmp_path: Path) -> None:
    found = a_module(tmp_path, '"""A sample module for the check."""\nimport json\n')
    assert found == []
