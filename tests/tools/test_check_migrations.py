"""The migration lock, and what it does when a migration changes."""

from __future__ import annotations

import pytest

from scowbox.store.migrations import MIGRATIONS, Migration
from scowbox.tools.check_migrations import (
    digest,
    findings,
    held,
    lines,
    lock_path,
    main,
)


def test_the_lock_file_is_in_the_checkout() -> None:
    assert lock_path().exists()


def test_this_package_has_nothing_to_report() -> None:
    assert findings() == []


def test_the_check_exits_clean(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    assert "check_migrations" in capsys.readouterr().out


def test_the_lock_holds_a_line_for_every_migration() -> None:
    assert len(held()) == len(MIGRATIONS)


def test_a_digest_is_stable_for_the_same_statements() -> None:
    one = Migration(1, "a", ("CREATE TABLE t (a INTEGER)",))
    again = Migration(1, "a", ("CREATE TABLE t (a INTEGER)",))
    assert digest(one) == digest(again)


def test_a_digest_ignores_surrounding_whitespace() -> None:
    plain = Migration(1, "a", ("CREATE TABLE t (a INTEGER)",))
    padded = Migration(1, "a", ("\n            CREATE TABLE t (a INTEGER)\n            ",))
    assert digest(plain) == digest(padded)


def test_a_changed_statement_changes_the_digest() -> None:
    one = Migration(1, "a", ("CREATE TABLE t (a INTEGER)",))
    other = Migration(1, "a", ("CREATE TABLE t (a TEXT)",))
    assert digest(one) != digest(other)


def test_a_missing_lock_is_reported() -> None:
    assert "is missing" in findings(lines(), [])[0]


def test_a_changed_migration_is_reported() -> None:
    tampered = [line.replace(line.split()[1], "0" * 16) for line in lines()]
    found = findings(lines(), tampered)
    assert "has changed since it was locked" in found[0]


def test_a_new_migration_is_reported_until_it_is_locked() -> None:
    short = lines()[:-1]
    found = findings(lines(), short)
    assert "is not in migrations.lock" in found[0]


def test_a_migration_taken_out_of_the_code_is_reported() -> None:
    extra = [*lines(), " 99 " + "0" * 16 + " invented"]
    found = findings(lines(), extra)
    assert "no longer in the code" in found[0]


def test_the_lock_lines_carry_the_version_and_the_name() -> None:
    first = lines()[0].split()
    assert first[0] == "1"
    assert first[2] == "channel"
