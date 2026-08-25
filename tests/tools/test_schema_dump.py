"""The schema document is generated, and CI checks it did not go stale."""

from __future__ import annotations

from pathlib import Path

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


def test_a_stale_document_is_found(tmp_path: Path) -> None:
    where = tmp_path / "schema.md"
    write(where)
    where.write_text(where.read_text(encoding="utf-8") + "\nelse\n", encoding="utf-8")
    assert "out of date" in findings(where)[0]


def test_a_missing_document_is_found(tmp_path: Path) -> None:
    assert "is missing" in findings(tmp_path / "nothing.md")[0]


def test_a_freshly_written_document_is_current(tmp_path: Path) -> None:
    where = tmp_path / "deep" / "schema.md"
    assert write(where) == where
    assert findings(where) == []


def test_writing_the_document_reports_where(capsys: pytest.CaptureFixture[str]) -> None:
    held = document_path().read_text(encoding="utf-8")
    assert main([]) == 0
    assert "wrote" in capsys.readouterr().out
    assert document_path().read_text(encoding="utf-8") == held
