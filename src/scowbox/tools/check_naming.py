"""Check: a test name is a claim about the code.

``test_measure`` says which function ran. ``test_a_light_reading_past_the_box
_depth_is_refused`` says what is true, and when it goes red the name is already
the bug report. The difference costs nothing to write and is the whole value of
the suite six months later.

Two rules, both crude on purpose. A name is at least four words long, because
three is not a sentence. And a name contains none of the words that sound like
a claim and are not: whether something *works*, is *correct*, is *handled*, is
*valid*. Those describe the author's confidence rather than the behaviour.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from scowbox.tools.scan import report, suite_files

NAME = "check_naming"
MIN_WORDS = 4

VAGUE = frozenset(
    {
        "works",
        "correct",
        "correctly",
        "properly",
        "successfully",
        "handles",
        "handled",
        "valid",
        "invalid",
        "ok",
        "stuff",
        "thing",
        "things",
    }
)
"""Words that sound like a claim and are not.

Three words came off this list after they were tried. ``test`` and ``tests``
are what half the check tools are about, and ``working`` is what a dredge does.
A word list that argues with the domain produces findings nobody can act on,
and the check gets turned off rather than the names getting better."""


def words(name: str) -> list[str]:
    """The words of a test name, without the ``test_`` on the front."""
    return [word for word in name.removeprefix("test_").split("_") if word]


def names(paths: list[Path] | None = None) -> list[tuple[str, str]]:
    """Every test function in the suite, with the file it is in."""
    found = []
    for path in paths if paths is not None else suite_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                found.append((str(path.name), node.name))
    return found


def findings(paths: list[Path] | None = None) -> list[str]:
    """Every test name that is not a claim."""
    out = []
    for where, name in names(paths):
        parts = words(name)
        if len(parts) < MIN_WORDS:
            out.append(f"{where}::{name} is {len(parts)} words, under {MIN_WORDS}")
        vague = sorted(set(parts) & VAGUE)
        if vague:
            out.append(f"{where}::{name} says {', '.join(vague)}, which claims nothing")
    return out


def main() -> int:
    """Run the check and return the exit status."""
    return report(NAME, findings())


if __name__ == "__main__":
    sys.exit(main())
