"""The release check, on this checkout and on three numbers that disagree."""

from __future__ import annotations

import pytest

from scowbox import __version__
from scowbox.tools.release_check import (
    changelog_path,
    entries,
    findings,
    main,
    project_version,
)


def test_this_checkout_has_nothing_to_report() -> None:
    assert findings() == []


def test_the_check_exits_clean(capsys: pytest.CaptureFixture[str]) -> None:
    assert main() == 0
    assert "release_check" in capsys.readouterr().out


def test_the_changelog_is_in_the_checkout() -> None:
    assert changelog_path().exists()


def test_the_three_copies_agree() -> None:
    assert project_version() == __version__
    assert entries()[0] == __version__


def test_the_changelog_entries_come_newest_first() -> None:
    found = entries()
    assert found == sorted(found, reverse=True)
    assert found[0] == __version__
    assert "0.1.0" in found


def test_a_version_that_is_not_three_parts_is_found() -> None:
    found = findings("1.0")
    assert "not a three part version" in found[0]


def test_a_package_ahead_of_the_project_file_is_found() -> None:
    found = findings("9.9.9")
    assert any("pyproject.toml says" in line for line in found)


def test_a_package_ahead_of_the_changelog_is_found() -> None:
    found = findings("9.9.9")
    assert any("the top of CHANGELOG.md says" in line for line in found)


def test_a_version_is_read_out_of_the_project_file() -> None:
    assert project_version('version = "2.3.4"\n') == "2.3.4"
    assert project_version("nothing here\n") is None


def test_the_entries_are_read_off_the_headings() -> None:
    assert entries("# Changelog\n\n## 2.0.0\n\n## 1.9.0\n") == ["2.0.0", "1.9.0"]


def test_a_missing_changelog_is_found() -> None:
    where = changelog_path()
    held = where.read_text(encoding="utf-8")
    try:
        where.unlink()
        found = findings()
        assert any("CHANGELOG.md is missing" in line for line in found)
    finally:
        where.write_text(held, encoding="utf-8")


def test_a_changelog_with_no_entries_is_found() -> None:
    where = changelog_path()
    held = where.read_text(encoding="utf-8")
    try:
        where.write_text("# Changelog\n\nnothing yet\n", encoding="utf-8")
        assert any("no version entries" in line for line in findings())
    finally:
        where.write_text(held, encoding="utf-8")


def test_the_same_version_twice_is_found() -> None:
    where = changelog_path()
    held = where.read_text(encoding="utf-8")
    try:
        where.write_text(f"# Changelog\n\n## {__version__}\n\n## {__version__}\n", encoding="utf-8")
        assert any("the same version twice" in line for line in findings())
    finally:
        where.write_text(held, encoding="utf-8")


def test_the_check_fails_when_something_is_wrong(capsys: pytest.CaptureFixture[str]) -> None:
    where = changelog_path()
    held = where.read_text(encoding="utf-8")
    try:
        where.write_text("# Changelog\n\n## 9.9.9\n", encoding="utf-8")
        assert main() == 1
        assert "release_check" in capsys.readouterr().out
    finally:
        where.write_text(held, encoding="utf-8")
