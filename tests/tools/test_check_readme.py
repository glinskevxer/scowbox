"""The README check, on this README and on a command that has gone."""

from __future__ import annotations

import pytest

from scowbox.tools.check_readme import (
    findings,
    invocations,
    known,
    main,
    options,
    readme_path,
    readme_text,
    words,
)


def test_the_readme_is_in_the_checkout() -> None:
    assert readme_path().exists()


def test_this_readme_has_nothing_to_report() -> None:
    assert findings() == []


def test_the_check_exits_clean(capsys: pytest.CaptureFixture[str]) -> None:
    assert main() == 0
    assert "check_readme" in capsys.readouterr().out


def test_the_readme_types_several_commands() -> None:
    assert len(invocations(readme_text())) > 5


def test_the_command_words_drop_the_options_and_their_values() -> None:
    typed = "--book harbour.sqlite3 reach add RCH-012 Lower --begin 100+00".split()
    assert words(typed) == ["reach", "add", "RCH-012", "Lower"]


def test_the_long_options_come_back() -> None:
    typed = "--book harbour.sqlite3 reach add RCH-012 --begin 100+00 -x".split()
    assert options(typed) == ["--book", "--begin"]


def test_a_command_takes_the_options_it_declares() -> None:
    allowed = known(["reach", "add"])
    assert "--begin" in allowed
    assert "--bottom" in allowed
    assert "--book" in allowed


def test_a_command_does_not_take_another_command_s_options() -> None:
    assert "--begin" not in known(["scow", "add"])


def test_a_command_that_has_gone_is_found() -> None:
    found = findings("    scowbox --book b.sqlite3 reach invent RCH-012\n")
    assert "'invent' is not a command" in found[0]


def test_an_option_a_command_does_not_take_is_found() -> None:
    found = findings("    scowbox --book b.sqlite3 scow list --begin 100+00\n")
    assert "does not take it" in found[0]


def test_a_document_that_is_not_there_is_found() -> None:
    found = findings("see `docs/invented.md` for more\n")
    assert found == ["the README points at docs/invented.md, which is not there"]


def test_a_document_that_is_there_is_left_alone() -> None:
    assert findings("see `docs/schema.md` for more\n") == []
