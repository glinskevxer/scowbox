"""The glossary is generated from the enums the package already has."""

from __future__ import annotations

from pathlib import Path

import pytest

from scowbox.model.channel import Method
from scowbox.model.shift import Reason
from scowbox.tools.build_glossary import (
    document_path,
    findings,
    glossary,
    main,
    terms,
    vocabularies,
    write,
)


def test_the_document_is_in_the_checkout() -> None:
    assert document_path().exists()


def test_the_document_matches_the_enums() -> None:
    assert findings() == []


def test_the_check_exits_clean(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--check"]) == 0
    assert "nothing to report" in capsys.readouterr().out


def test_the_vocabularies_come_from_the_model() -> None:
    found = {vocabulary for _, vocabulary in vocabularies()}
    assert Method in found
    assert Reason in found


def test_a_vocabulary_is_listed_once_under_its_own_module() -> None:
    pairs = [(where, v.__name__) for where, v in vocabularies() if v is Method]
    assert pairs == [("scowbox.model.channel", "Method")]


def test_the_check_tools_are_left_out() -> None:
    assert not any(where.startswith("scowbox.tools.") for where, _ in vocabularies())


def test_every_member_is_a_term() -> None:
    text = "\n".join(glossary())
    for reason in Reason:
        assert f"**{reason.value}**" in text


def test_the_class_docstring_heads_its_section() -> None:
    text = "\n".join(glossary())
    assert "How a reach's pay quantity is measured." in text


def test_the_terms_are_the_member_values() -> None:
    found = terms()
    assert "channel traffic" in found
    assert "ocean site" in found
    assert len(found) > 25


def test_a_stale_document_is_found(tmp_path: Path) -> None:
    where = tmp_path / "glossary.md"
    write(where)
    where.write_text(where.read_text(encoding="utf-8") + "\nelse\n", encoding="utf-8")
    assert "out of date" in findings(where)[0]


def test_a_missing_document_is_found(tmp_path: Path) -> None:
    assert "is missing" in findings(tmp_path / "nothing.md")[0]


def test_a_freshly_written_document_is_current(tmp_path: Path) -> None:
    where = tmp_path / "deep" / "glossary.md"
    assert write(where) == where
    assert findings(where) == []


def test_writing_the_glossary_puts_it_back(capsys: pytest.CaptureFixture[str]) -> None:
    held = document_path().read_text(encoding="utf-8")
    assert main([]) == 0
    assert "terms from scowbox" in capsys.readouterr().out
    assert document_path().read_text(encoding="utf-8") == held


def test_the_checkout_copy_is_the_one_the_check_reads() -> None:
    assert write() == document_path()
    assert findings() == []


def test_an_enum_with_no_docstring_still_gets_a_section() -> None:
    text = "\n".join(glossary())
    assert text.count("## ") == len(vocabularies())
