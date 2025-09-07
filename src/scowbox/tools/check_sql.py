"""Check: values reach sqlite as parameters, never as text.

The statements in this package are built with f-strings, and that is on
purpose: the column lists are long, they are written once at the top of each
repository, and repeating them inside every statement is how one of them ends
up in a different order from the others.

What must never be interpolated is a value. So the rule is narrow enough to be
checkable: an f-string handed to ``execute`` may interpolate a module level
constant and nothing else. A name in lower case, an attribute, a call, a
subscript, anything computed, is a finding, whether or not it happens to be
safe today.
"""

from __future__ import annotations

import ast
import sys

from scowbox.tools.scan import Module, modules, report

NAME = "check_sql"
RUNNERS = ("execute", "executemany", "executescript")
GUARDS = ("sql_identifier", "sql_integer")
"""The two helpers allowed to produce a spliced fragment. Sqlite takes neither
an identifier nor a pragma argument as a parameter, so those two cases have to
be built by hand, and they are built in one place that validates them."""


def findings(found: list[Module] | None = None) -> list[str]:
    """Every statement that interpolates something other than a constant."""
    out = []
    for module in found if found is not None else modules():
        out.extend(_module(module))
    return out


def _module(module: Module) -> list[str]:
    constants = _constants(module)
    out = []
    for node in ast.walk(module.tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr not in RUNNERS:
            continue
        for argument in node.args[:1]:
            out.extend(_statement(module, node, argument, constants))
    return out


def _statement(
    module: Module, call: ast.Call, argument: ast.expr, constants: set[str]
) -> list[str]:
    out = []
    for piece in _pieces(argument):
        if not isinstance(piece, ast.FormattedValue):
            continue
        inner = piece.value
        if isinstance(inner, ast.Name) and inner.id in constants:
            continue
        if isinstance(inner, ast.Call) and _guarded(inner):
            continue
        out.append(
            f"{module.where} line {call.lineno} interpolates {ast.unparse(inner)} into a statement"
        )
    return out


def _guarded(call: ast.Call) -> bool:
    """True when the fragment came out of one of the validating helpers."""
    if isinstance(call.func, ast.Name):
        return call.func.id in GUARDS
    if isinstance(call.func, ast.Attribute):
        return call.func.attr in GUARDS
    return False


def _pieces(argument: ast.expr) -> list[ast.expr]:
    if isinstance(argument, ast.JoinedStr):
        return list(argument.values)
    if isinstance(argument, ast.BinOp):
        return _pieces(argument.left) + _pieces(argument.right)
    return []


def _constants(module: Module) -> set[str]:
    """Module level names in upper case, which are the only ones allowed in."""
    found = set()
    for node in module.tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    found.add(target.id)
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id.isupper()
        ):
            found.add(node.target.id)
    return found


def main() -> int:
    """Run the check and return the exit status."""
    return report(NAME, findings())


if __name__ == "__main__":
    sys.exit(main())
