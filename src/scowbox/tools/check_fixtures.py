"""Check: a fixture that opens a book closes it.

A fixture that returns an open connection leaks it. On Python 3.12 nothing
happens and the suite is green. On 3.13 the garbage collector raises
ResourceWarning when it gets round to the connection, ``filterwarnings =
["error"]`` turns that into a failure, and it is attributed to whichever test
the collector happened to interrupt. Five fixtures did this here before the
3.13 leg was added, and the failure it produced named none of them.

So a fixture that opens anything opens it in a ``with`` and yields inside it.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from scowbox.tools.scan import report, suite_files

NAME = "check_fixtures"
OPENERS = ("book", "opened", "connect", "TemporaryDirectory", "NamedTemporaryFile")


def is_fixture(node: ast.FunctionDef) -> bool:
    """True when the function is decorated as a pytest fixture."""
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(target, ast.Attribute) and target.attr == "fixture":
            return True
        if isinstance(target, ast.Name) and target.id == "fixture":
            return True
    return False


def opens(node: ast.FunctionDef) -> list[str]:
    """Every opener the fixture calls."""
    found = []
    for inner in ast.walk(node):
        if not isinstance(inner, ast.Call):
            continue
        name = None
        if isinstance(inner.func, ast.Name):
            name = inner.func.id
        elif isinstance(inner.func, ast.Attribute):
            name = inner.func.attr
        if name in OPENERS:
            found.append(name)
    return found


def findings(paths: list[Path] | None = None) -> list[str]:
    """Every fixture that opens something outside a ``with``."""
    out = []
    for path in paths if paths is not None else suite_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or not is_fixture(node):
                continue
            opened = opens(node)
            if not opened:
                continue
            if not any(isinstance(inner, ast.With) for inner in ast.walk(node)):
                out.append(f"{path.name}::{node.name} calls {opened[0]}() and never closes it")
    return out


def main() -> int:
    """Run the check and return the exit status."""
    return report(NAME, findings())


if __name__ == "__main__":
    sys.exit(main())
