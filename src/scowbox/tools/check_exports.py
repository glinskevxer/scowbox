"""Check: a public name is used somewhere.

Dead code in a package like this is not harmless. Every public function is a
promise about what the module does, and one nothing calls is a promise nobody
checked. Worse, it goes on being maintained: it gets renamed with the rest, it
gets a docstring, it turns up in a review, and none of that touches anything
that runs.

Decorated functions are exempt. A click command is reached through the group it
is hung on and never by its own name, and so is a pytest fixture.
"""

from __future__ import annotations

import ast
import sys

from scowbox.tools.scan import Module, modules, report, suite_files

NAME = "check_exports"
ALWAYS_USED = frozenset({"main", "run"})


def defined(module: Module) -> list[str]:
    """Every public module level name this module defines."""
    found = []
    for node in module.tree.body:
        if isinstance(node, ast.FunctionDef | ast.ClassDef):
            if node.name.startswith("_") or node.decorator_list:
                continue
            found.append(node.name)
    return found


def used(found: list[Module] | None = None) -> dict[str, set[str]]:
    """Every name used, and the modules that use it."""
    where: dict[str, set[str]] = {}
    sources = list(found if found is not None else modules())
    trees = [(module.name, module.tree) for module in sources]
    for path in suite_files():
        trees.append((f"tests.{path.stem}", ast.parse(path.read_text(encoding="utf-8"))))
    for name, tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                where.setdefault(node.id, set()).add(name)
            elif isinstance(node, ast.Attribute):
                where.setdefault(node.attr, set()).add(name)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    where.setdefault(alias.name, set()).add(name)
    return where


def findings(found: list[Module] | None = None) -> list[str]:
    """Every public name used only in the module that defines it."""
    sources = list(found if found is not None else modules())
    where = used(sources)
    out = []
    for module in sources:
        for name in defined(module):
            if name in ALWAYS_USED:
                continue
            elsewhere = where.get(name, set()) - {module.name}
            if not elsewhere:
                out.append(f"{module.where}.{name} is used nowhere else")
    return out


def main() -> int:
    """Run the check and return the exit status."""
    return report(NAME, findings())


if __name__ == "__main__":
    sys.exit(main())
