"""Putting text in columns.

Reports on this job are read on a terminal and printed to paper at eighty
columns, so the width is fixed and the columns are built rather than fitted. A
table that widens to its content looks fine on the screen it was written on and
wraps into nonsense on the one it is read on.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

WIDTH = 78


def rule(character: str = "-") -> str:
    return character * WIDTH


def heading(title: str, under: str = "=") -> list[str]:
    """A title with a rule under it."""
    return [title, under * min(len(title), WIDTH)]


def pair(label: str, value: str, width: int = 14) -> str:
    """A label and its value, the labels lining up down the page."""
    return f"{label:<{width}}{value}"


def row(cells: Sequence[str], widths: Sequence[int]) -> str:
    """One line of a table, right aligning anything that starts with a digit."""
    if len(cells) != len(widths):
        raise ValueError("a row needs one width for every cell")
    out = []
    for cell, width in zip(cells, widths, strict=True):
        text = cell if len(cell) <= width else cell[: width - 1] + "…"
        out.append(f"{text:>{width}}" if _numeric(text) else f"{text:<{width}}")
    return " ".join(out).rstrip()


def table(
    headings: Sequence[str], body: Iterable[Sequence[str]], widths: Sequence[int]
) -> list[str]:
    """A heading row, a rule and the body."""
    lines = [row(headings, widths)]
    lines.append(rule())
    lines.extend(row(cells, widths) for cells in body)
    return lines


def total_line(label: str, value: str, widths: Sequence[int]) -> str:
    """A total that lines up under the last column of a table."""
    filler = [""] * (len(widths) - 2)
    return row([label, *filler, value], widths)


def _numeric(text: str) -> bool:
    head = text.lstrip("$-+(")
    return bool(head) and head[0].isdigit()


def indent(lines: Iterable[str], by: int = 2) -> list[str]:
    return [" " * by + line if line else line for line in lines]


def blank() -> str:
    return ""
