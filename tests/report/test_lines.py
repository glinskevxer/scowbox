"""Columns are built to a fixed width, not fitted to the content."""

from __future__ import annotations

import pytest

from scowbox.report.lines import (
    WIDTH,
    heading,
    indent,
    pair,
    row,
    rule,
    table,
    total_line,
)


def test_a_rule_is_the_page_width() -> None:
    assert len(rule()) == WIDTH
    assert rule("=")[0] == "="


def test_a_heading_carries_a_rule_no_longer_than_itself() -> None:
    lines = heading("Day report")
    assert lines[0] == "Day report"
    assert lines[1] == "=" * len("Day report")


def test_a_pair_lines_the_labels_up() -> None:
    assert pair("gross", "12.0 hours") == "gross         12.0 hours"


def test_text_cells_go_left_and_numbers_go_right() -> None:
    assert row(("SH-1", "12.0"), (8, 8)) == "SH-1         12.0"


def test_money_counts_as_a_number() -> None:
    assert row(("earned", "$1.00"), (8, 8)) == "earned      $1.00"


def test_a_cell_too_wide_is_cut_with_an_ellipsis() -> None:
    assert row(("a very long description",), (10,)) == "a very lo…"


def test_a_row_needs_a_width_for_every_cell() -> None:
    with pytest.raises(ValueError, match="one width"):
        row(("a", "b"), (8,))


def test_a_row_does_not_carry_trailing_space() -> None:
    assert row(("a", "b"), (8, 8)) == "a        b"


def test_a_table_has_a_heading_and_a_rule() -> None:
    lines = table(("shift", "hours"), [("SH-1", "12.0")], (8, 8))
    assert lines[0].startswith("shift")
    assert lines[1] == rule()
    assert lines[2].startswith("SH-1")


def test_an_empty_table_is_still_a_heading() -> None:
    assert len(table(("shift",), [], (8,))) == 2


def test_a_total_lines_up_under_the_last_column() -> None:
    line = total_line("total", "1,234", (8, 8, 8))
    assert line.endswith("1,234")
    assert line.startswith("total")


def test_indent_leaves_blank_lines_alone() -> None:
    assert indent(["a", "", "b"]) == ["  a", "", "  b"]
