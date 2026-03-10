"""The design check, on this note and on a name that has gone."""

from __future__ import annotations

import pytest

from scowbox.tools.check_design import document_path, findings, main, named, resolves


def test_the_note_is_in_the_checkout() -> None:
    assert document_path().exists()


def test_this_note_has_nothing_to_report() -> None:
    assert findings() == []


def test_the_check_exits_clean(capsys: pytest.CaptureFixture[str]) -> None:
    assert main() == 0
    assert "check_design" in capsys.readouterr().out


def test_the_note_names_a_lot_of_modules() -> None:
    assert len(named()) > 15


def test_only_dotted_names_of_this_package_are_taken() -> None:
    found = named("see `scowbox.units.money` and `pytest.raises` and `scowbox` and `init`")
    assert found == ["scowbox.units.money"]


def test_a_name_is_taken_once_however_often_it_appears() -> None:
    assert named("`scowbox.errors` twice: `scowbox.errors`") == ["scowbox.errors"]


def test_a_module_of_the_package_resolves() -> None:
    assert resolves("scowbox.units.money")


def test_an_attribute_of_a_module_resolves() -> None:
    assert resolves("scowbox.store.sqlite.opened")
    assert resolves("scowbox.units.money.Money")


def test_a_module_that_has_gone_does_not_resolve() -> None:
    assert not resolves("scowbox.units.fathoms")


def test_an_attribute_that_has_gone_does_not_resolve() -> None:
    assert not resolves("scowbox.units.money.Doubloon")


def test_a_note_naming_something_that_has_gone_is_found() -> None:
    found = findings("The rules live in `scowbox.measure.invented`.")
    assert found == ["docs/design.md names scowbox.measure.invented, which is not there"]
