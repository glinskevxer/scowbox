"""The naming check, on this suite and on names that claim nothing."""

from __future__ import annotations

from pathlib import Path

import pytest

from scowbox.tools.check_naming import VAGUE, findings, main, names, words


def a_suite(tmp_path: Path, body: str) -> list[str]:
    where = tmp_path / "test_sample.py"
    where.write_text('"""A sample suite."""\n' + body, encoding="utf-8")
    return findings([where])


def test_this_suite_has_nothing_to_report() -> None:
    assert findings() == []


def test_the_check_exits_clean(capsys: pytest.CaptureFixture[str]) -> None:
    assert main() == 0
    assert "check_naming" in capsys.readouterr().out


def test_the_suite_holds_a_lot_of_named_claims() -> None:
    assert len(names()) > 500


def test_the_prefix_is_not_one_of_the_words() -> None:
    assert words("test_a_light_reading_is_refused") == ["a", "light", "reading", "is", "refused"]


def test_a_short_name_is_found(tmp_path: Path) -> None:
    found = a_suite(tmp_path, "def test_measure_works_ok() -> None:\n    pass\n")
    assert any("3 words, under 4" in line for line in found)


def test_a_vague_word_is_found(tmp_path: Path) -> None:
    found = a_suite(tmp_path, "def test_the_box_measure_works_as_expected() -> None:\n    pass\n")
    assert any("says works, which claims nothing" in line for line in found)


def test_several_vague_words_come_back_in_one_finding(tmp_path: Path) -> None:
    found = a_suite(tmp_path, "def test_the_thing_works_correctly_here() -> None:\n    pass\n")
    assert any("correctly, thing, works" in line for line in found)


def test_a_claim_is_left_alone(tmp_path: Path) -> None:
    found = a_suite(
        tmp_path,
        "def test_a_light_reading_past_the_box_depth_is_refused() -> None:\n    pass\n",
    )
    assert found == []


def test_a_helper_that_is_not_a_test_is_ignored(tmp_path: Path) -> None:
    found = a_suite(tmp_path, "def a_scow() -> None:\n    pass\n")
    assert found == []


def test_the_word_list_leaves_the_domain_alone() -> None:
    assert "working" not in VAGUE
    assert "test" not in VAGUE
