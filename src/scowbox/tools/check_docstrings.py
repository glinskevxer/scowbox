"""Check: every module, class and public function says what it is for.

Not because a docstring is a virtue. Because the modules here carry the
reasoning that the code cannot: why the survey governs inside the tolerance,
why a scow with no trips is unmeasured rather than zero. A module with no
docstring is one where that reasoning was never written down, and it does not
come back.

Private helpers are exempt. A leading underscore is a promise that the thing is
readable in the twenty lines around it.
"""

from __future__ import annotations

import ast
import sys

from scowbox.tools.scan import Module, modules, report

NAME = "check_docstrings"
MIN_WORDS = 4


def findings(found: list[Module] | None = None) -> list[str]:
    """Every place a docstring is missing or too thin to say anything."""
    out = []
    for module in found if found is not None else modules():
        out.extend(_module(module))
    return out


def _module(module: Module) -> list[str]:
    out = []
    text = ast.get_docstring(module.tree)
    if not text:
        out.append(f"{module.where} has no module docstring")
    elif _thin(text):
        out.append(f"{module.where} has a module docstring of under {MIN_WORDS} words")
    for function in module.functions():
        if function.name.startswith("_"):
            continue
        if not ast.get_docstring(function):
            out.append(f"{module.where}.{function.name} has no docstring")
    for defined in module.classes():
        if not ast.get_docstring(defined):
            out.append(f"{module.where}.{defined.name} has no docstring")
    return out


def _thin(text: str) -> bool:
    return len(text.split()) < MIN_WORDS


def main() -> int:
    """Run the check and return the exit status."""
    return report(NAME, findings())


if __name__ == "__main__":
    sys.exit(main())
