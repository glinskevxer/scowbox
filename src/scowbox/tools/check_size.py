"""Check: a module is readable in one sitting and a function in one screen.

Neither number is principled. They were set at half again the largest thing in
the package on the day the check was written, which was a hundred and eleven
statements for a module and twenty eight for a function. That is a ceiling
rather than a target: it does not ask anything to get smaller, it says when
something has grown past the shape everything else here has.

The measure is statements, not lines, so a docstring that explains why a rule
exists costs nothing. That is deliberate: the docstrings here are most of the
reasoning and a check that penalised them would be the wrong check.
"""

from __future__ import annotations

import ast
import sys

from scowbox.tools.scan import Module, modules, report

NAME = "check_size"
MODULE_CEILING = 165
FUNCTION_CEILING = 42


def statements(node: ast.AST) -> int:
    """How many statements a node holds, docstrings and comments excluded."""
    return sum(
        1 for inner in ast.walk(node) if isinstance(inner, ast.stmt) and not _is_docstring(inner)
    )


def _is_docstring(node: ast.stmt) -> bool:
    return isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)


def module_size(module: Module) -> int:
    """Statements in a module, its functions and classes included."""
    return statements(module.tree)


def function_sizes(module: Module) -> list[tuple[str, int]]:
    """Every function in a module, nested ones included, with its size."""
    found = []
    for node in ast.walk(module.tree):
        if isinstance(node, ast.FunctionDef):
            found.append((node.name, statements(node) - 1))
    return found


def findings(found: list[Module] | None = None) -> list[str]:
    """Every module or function past its ceiling."""
    out = []
    for module in found if found is not None else modules():
        size = module_size(module)
        if size > MODULE_CEILING:
            out.append(f"{module.where} is {size} statements, past the {MODULE_CEILING} ceiling")
        out.extend(
            f"{module.where}.{name} is {size} statements, past the {FUNCTION_CEILING} ceiling"
            for name, size in function_sizes(module)
            if size > FUNCTION_CEILING
        )
    return out


def main() -> int:
    """Run the check and return the exit status."""
    return report(NAME, findings())


if __name__ == "__main__":
    sys.exit(main())
