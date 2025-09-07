"""The sql check, on this package and on a statement built from a value."""

from __future__ import annotations

from pathlib import Path

import pytest

from scowbox.tools.check_sql import findings, main
from scowbox.tools.scan import parse


def a_module(tmp_path: Path, body: str) -> list[str]:
    where = tmp_path / "store"
    where.mkdir(exist_ok=True)
    module = where / "sample.py"
    module.write_text('"""A sample module for the check."""\n' + body, encoding="utf-8")
    return findings([parse(module, tmp_path)])


def test_this_package_passes() -> None:
    assert findings() == []


def test_the_check_exits_clean(capsys: pytest.CaptureFixture[str]) -> None:
    assert main() == 0
    assert "check_sql" in capsys.readouterr().out


def test_a_plain_statement_is_fine(tmp_path: Path) -> None:
    found = a_module(
        tmp_path, "def go(c, ident):\n    c.execute('SELECT a FROM t WHERE b = ?', (ident,))\n"
    )
    assert found == []


def test_a_column_constant_is_allowed(tmp_path: Path) -> None:
    found = a_module(
        tmp_path,
        'COLUMNS = "a, b"\n\n\ndef go(c):\n    c.execute(f"SELECT {COLUMNS} FROM t")\n',
    )
    assert found == []


def test_a_value_interpolated_into_a_statement_is_found(tmp_path: Path) -> None:
    found = a_module(
        tmp_path, 'def go(c, ident):\n    c.execute(f"SELECT a FROM t WHERE b = {ident}")\n'
    )
    assert "interpolates ident" in found[0]


def test_an_attribute_is_found(tmp_path: Path) -> None:
    found = a_module(
        tmp_path, 'def go(c, r):\n    c.execute(f"SELECT a FROM t WHERE b = {r.ident}")\n'
    )
    assert "interpolates r.ident" in found[0]


def test_a_call_is_found(tmp_path: Path) -> None:
    found = a_module(tmp_path, 'def go(c, r):\n    c.execute(f"SELECT a FROM {name(r)}")\n')
    assert "interpolates name(r)" in found[0]


def test_a_lower_case_module_name_is_not_a_constant(tmp_path: Path) -> None:
    found = a_module(
        tmp_path, 'columns = "a, b"\n\n\ndef go(c):\n    c.execute(f"SELECT {columns} FROM t")\n'
    )
    assert "interpolates columns" in found[0]


def test_executemany_is_checked_too(tmp_path: Path) -> None:
    found = a_module(
        tmp_path,
        'def go(c, ident, rows):\n    c.executemany(f"INSERT INTO {ident} VALUES (?)", rows)\n',
    )
    assert "interpolates ident" in found[0]


def test_an_annotated_constant_is_allowed(tmp_path: Path) -> None:
    found = a_module(
        tmp_path,
        'COLUMNS: str = "a, b"\n\n\ndef go(c):\n    c.execute(f"SELECT {COLUMNS} FROM t")\n',
    )
    assert found == []


def test_a_validated_identifier_is_allowed(tmp_path: Path) -> None:
    found = a_module(
        tmp_path,
        "from scowbox.store.sqlite import sql_identifier\n\n\n"
        'def go(c, name):\n    c.execute(f"SELECT count(*) FROM {sql_identifier(name)}")\n',
    )
    assert found == []


def test_a_validated_integer_is_allowed(tmp_path: Path) -> None:
    found = a_module(
        tmp_path,
        "from scowbox.store.sqlite import sql_integer\n\n\n"
        'def go(c, v):\n    c.execute(f"PRAGMA user_version = {sql_integer(v)}")\n',
    )
    assert found == []


def test_another_helper_is_not_a_guard(tmp_path: Path) -> None:
    found = a_module(
        tmp_path, 'def go(c, name):\n    c.execute(f"SELECT count(*) FROM {clean(name)}")\n'
    )
    assert "interpolates clean(name)" in found[0]


def test_a_statement_spliced_together_is_still_checked(tmp_path: Path) -> None:
    found = a_module(
        tmp_path,
        'def go(c, ident):\n    c.execute("SELECT a FROM t" f" WHERE b = {ident}")\n',
    )
    assert "interpolates ident" in found[0]
