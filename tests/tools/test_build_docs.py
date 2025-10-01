"""The command reference is generated, and CI checks it did not go stale."""

from __future__ import annotations

import pytest

from scowbox.tools.build_docs import document_path, findings, main, reference, write
from scowbox.tools.check_help import commands


def test_the_document_is_in_the_checkout() -> None:
    assert document_path().exists()


def test_the_document_matches_the_command_tree() -> None:
    assert findings() == []


def test_the_check_exits_clean(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--check"]) == 0
    assert "nothing to report" in capsys.readouterr().out


def test_every_command_has_a_heading() -> None:
    text = "\n".join(reference())
    assert text.count("## `scowbox ") == commands() - 1


def test_the_top_level_group_is_not_its_own_entry() -> None:
    assert "## `cli`" not in "\n".join(reference())


def test_a_command_carries_its_first_line_of_help() -> None:
    text = "\n".join(reference())
    assert "## `scowbox reach add`" in text
    assert "Put a reach in the book." in text


def test_arguments_are_listed() -> None:
    text = "\n".join(reference())
    assert "Arguments: `ident`, `name`" in text


def test_options_are_listed_with_their_help() -> None:
    text = "\n".join(reference())
    assert "- `--bottom` — Bottom width in feet." in text


def test_the_book_option_is_on_the_top_level_group_only() -> None:
    text = "\n".join(reference())
    assert text.count("`--book`") == 0


def test_a_stale_document_is_found(capsys: pytest.CaptureFixture[str]) -> None:
    where = document_path()
    held = where.read_text(encoding="utf-8")
    try:
        where.write_text(held + "\nsomething else\n", encoding="utf-8")
        assert main(["--check"]) == 1
        assert "out of date" in capsys.readouterr().out
    finally:
        where.write_text(held, encoding="utf-8")


def test_a_missing_document_is_found() -> None:
    where = document_path()
    held = where.read_text(encoding="utf-8")
    try:
        where.unlink()
        assert "is missing" in findings()[0]
    finally:
        where.write_text(held, encoding="utf-8")


def test_writing_puts_it_back() -> None:
    held = document_path().read_text(encoding="utf-8")
    assert write() == document_path()
    assert document_path().read_text(encoding="utf-8") == held
