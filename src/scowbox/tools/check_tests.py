"""Check: every module is reached by the suite.

Not coverage. Coverage counts lines that ran, and a module can be at ninety
percent because something else imported it on the way past. This asks a
different question: is there a test that names this module and works it
directly.

A module nothing imports in the suite has no test of its own, whatever the
coverage report says about it.
"""

from __future__ import annotations

import ast
import sys

from scowbox.tools.scan import PACKAGE, Module, modules, project_root, report, suite_files

NAME = "check_tests"


def imported_by_suite() -> set[str]:
    """Every module of this package that a test module names.

    ``from scowbox.store import reaches`` names a module, and
    ``from scowbox.errors import RuleError`` names a class in one. Both look
    identical to the parser, so both dotted forms go in the set and the extra
    entries match nothing.
    """
    found: set[str] = set()
    for path in suite_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(PACKAGE):
                found.add(node.module)
                found.update(f"{node.module}.{alias.name}" for alias in node.names)
            elif isinstance(node, ast.Import):
                found.update(a.name for a in node.names if a.name.startswith(PACKAGE))
    return found


def suite_file_for(module: Module) -> str:
    """Where a test module for this one would live, whether or not it does."""
    parts = module.name.split(".")[1:]
    parts[-1] = f"test_{parts[-1]}.py"
    return "/".join(["tests", *parts])


def has_own_suite(module: Module) -> bool:
    """True when a test module sits where this module's tests would."""
    return (project_root() / suite_file_for(module)).exists()


def findings(reached: set[str] | None = None) -> list[str]:
    """Every module the suite neither names nor has a test file for.

    A command line module is driven through the composed command tree rather
    than imported, so naming is not the only evidence a module is tested. A
    file in the matching place counts too, and a module with neither has
    nothing behind it.
    """
    seen = reached if reached is not None else imported_by_suite()
    out = []
    for module in modules():
        if module.name == PACKAGE or module.name.endswith("__init__"):
            continue
        if module.path.name == "__init__.py":
            continue
        if module.name not in seen and not has_own_suite(module):
            out.append(f"{module.where} has no test that names it or file that mirrors it")
    return out


def main() -> int:
    """Run the check and return the exit status."""
    return report(NAME, findings())


if __name__ == "__main__":
    sys.exit(main())
