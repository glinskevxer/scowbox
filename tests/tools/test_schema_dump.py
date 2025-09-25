"""The schema document is generated, and CI checks it did not go stale."""

from __future__ import annotations

import pytest

from scowbox.store.migrations import latest
from scowbox.tools.schema_dump import (
    document_path,
    findings,
    live_schema,
    main,
    write,
)


def test_the_document_is_in_the_checkout() -> None:
    assert document_path().exists()


def test_the_document_matches_the_code() -> None:
    assert findings() == []


def test_the_check_exits_clean(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--check"]) == 0
    assert "nothing to report" in capsys.readouterr().out


def test_the_schema_names_the_version_it_was_taken_at() -> None:
    assert f"Schema version {latest()}." in live_schema()


def test_every_table_is_in_the_dump() -> None:
    text = "\n".join(live_schema())
    for table in ("reach", "survey", "sounding", "trip", "ticket", "estimate"):
        assert f"## {table} (table)" in text


def test_the_indexes_are_in_the_dump() -> None:
    text = "\n".join(live_schema())
    assert "## reach_by_group (index)" in text


def test_the_statements_are_fenced_as_sql() -> None:
    text = "\n".join(live_schema())
    assert text.count("```sql") == text.count("```") // 2


def test_the_migration_indentation_is_taken_off() -> None:
    text = "\n".join(live_schema())
    assert "\n    ident TEXT PRIMARY KEY," in text
    assert "\n                ident TEXT PRIMARY KEY," not in text


def test_a_stale_document_is_found(capsys: pytest.CaptureFixture[str]) -> None:
    where = document_path()
    held = where.read_text(encoding="utf-8")
    try:
        where.write_text(held + "\nsomething else\n", encoding="utf-8")
        assert findings() != []
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


def test_writing_puts_it_back(capsys: pytest.CaptureFixture[str]) -> None:
    held = document_path().read_text(encoding="utf-8")
    assert main([]) == 0
    assert "wrote" in capsys.readouterr().out
    assert document_path().read_text(encoding="utf-8") == held


def test_write_returns_where_it_wrote() -> None:
    assert write() == document_path()
