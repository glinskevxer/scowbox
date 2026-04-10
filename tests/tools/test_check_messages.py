"""The message check, on this package and on messages that read wrong."""

from __future__ import annotations

from pathlib import Path

import pytest

from scowbox.tools.check_messages import findings, main, messages
from scowbox.tools.scan import Module, parse


def a_module(tmp_path: Path, body: str) -> list[Module]:
    where = tmp_path / "measure"
    where.mkdir(exist_ok=True)
    module = where / "sample.py"
    module.write_text(
        '"""A sample module for the check."""\n'
        "from scowbox.errors import FieldError, RuleError\n\n\n" + body,
        encoding="utf-8",
    )
    return [parse(module, tmp_path)]


def test_this_package_has_nothing_to_report() -> None:
    assert findings() == []


def test_the_check_exits_clean(capsys: pytest.CaptureFixture[str]) -> None:
    assert main() == 0
    assert "check_messages" in capsys.readouterr().out


def test_a_message_ending_in_a_full_stop_is_found(tmp_path: Path) -> None:
    found = findings(a_module(tmp_path, "def go():\n    raise RuleError('the reach is closed.')\n"))
    assert "ends in a full stop" in found[0]


def test_a_capitalised_message_is_found(tmp_path: Path) -> None:
    found = findings(a_module(tmp_path, "def go():\n    raise RuleError('The reach is closed')\n"))
    assert "starts capitalised" in found[0]


def test_an_empty_message_is_found(tmp_path: Path) -> None:
    found = findings(a_module(tmp_path, "def go():\n    raise RuleError('')\n"))
    assert "empty message" in found[0]


def test_a_message_that_reads_right_is_left_alone(tmp_path: Path) -> None:
    found = findings(a_module(tmp_path, "def go():\n    raise RuleError('the reach is closed')\n"))
    assert found == []


def test_the_field_of_a_field_error_is_not_the_message(tmp_path: Path) -> None:
    found = findings(
        a_module(
            tmp_path,
            "def go():\n    raise FieldError('Bottom_width', 'a template needs a bottom')\n",
        )
    )
    assert found == []


def test_a_message_starting_interpolated_is_skipped(tmp_path: Path) -> None:
    found = findings(
        a_module(
            tmp_path,
            "def go(reach):\n    raise RuleError(f'{reach} is closed.')\n",
        )
    )
    assert found == []


def test_a_message_with_a_literal_head_is_still_read(tmp_path: Path) -> None:
    found = findings(
        a_module(
            tmp_path,
            "def go(reach):\n    raise RuleError(f'The reach {reach} is closed')\n",
        )
    )
    assert "starts capitalised" in found[0]


def test_an_identifier_in_the_message_is_not_a_capital(tmp_path: Path) -> None:
    found = findings(
        a_module(
            tmp_path,
            "def go():\n    raise RuleError('RCH-012 is measured by scow')\n",
        )
    )
    assert found == []


def test_the_messages_come_back_with_their_lines(tmp_path: Path) -> None:
    module = a_module(tmp_path, "def go():\n    raise RuleError('the reach is closed')\n")[0]
    found = messages(module)
    assert found[0][1] == "the reach is closed"
    assert found[0][0] > 1
