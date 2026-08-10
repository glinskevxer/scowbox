"""The standing rules, and the modules they say enforce them."""

from __future__ import annotations

import importlib

from scowbox.laws import LAWS, about, subjects


def test_every_law_names_a_subject_a_rule_and_a_module() -> None:
    for law in LAWS:
        assert law.subject.strip()
        assert law.rule.strip()
        assert law.where.startswith("scowbox.")


def test_the_subjects_are_distinct() -> None:
    assert len(set(subjects())) == len(subjects())


def test_every_module_a_law_names_is_importable() -> None:
    for law in LAWS:
        assert importlib.import_module(law.where)


def test_a_law_prints_as_one_line() -> None:
    line = LAWS[0].line()
    assert line.startswith("depths")
    assert "positive downward" in line


def test_the_rules_read_as_sentences_not_as_titles() -> None:
    for law in LAWS:
        assert law.rule[0].islower()
        assert not law.rule.endswith(".")


def test_there_are_enough_of_them_to_be_worth_printing() -> None:
    assert len(LAWS) >= 12


def test_a_word_in_a_subject_finds_its_rule() -> None:
    found = about("prism")
    assert any(law.subject == "prism" for law in found)


def test_a_word_in_the_wording_finds_it_too() -> None:
    found = about("overdepth")
    assert found
    assert all("overdepth" in law.rule.lower() or "overdepth" in law.subject for law in found)


def test_the_lookup_ignores_case_and_space() -> None:
    assert about("  PRISM  ") == about("prism")


def test_an_empty_word_asks_for_all_of_them() -> None:
    assert about("") == LAWS


def test_a_word_no_rule_mentions_finds_nothing() -> None:
    assert about("fathoms") == ()
