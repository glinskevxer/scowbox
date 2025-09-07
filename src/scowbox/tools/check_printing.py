"""Check: only the command line writes to the terminal.

A report is a list of lines. A rule returns a number. Neither of them prints,
and the reason is not tidiness: a renderer that prints cannot be tested without
capturing a stream, and a rule that prints cannot be called twice without
saying so out loud.

The command line prints. The check tools print. Nothing else does.
"""

from __future__ import annotations

import ast
import sys

from scowbox.tools.scan import Module, modules, report

NAME = "check_printing"
ALLOWED_MODULES = ("scowbox.cli.", "scowbox.tools.")


def findings(found: list[Module] | None = None) -> list[str]:
    """Every write to the terminal outside the layers allowed one."""
    out = []
    for module in found if found is not None else modules():
        if module.name.startswith(ALLOWED_MODULES):
            continue
        out.extend(_module(module))
    return out


def _module(module: Module) -> list[str]:
    out = []
    for node in ast.walk(module.tree):
        if not isinstance(node, ast.Call):
            continue
        what = _writes(node)
        if what:
            out.append(f"{module.where} line {node.lineno} calls {what}")
    return out


def _writes(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name) and node.func.id == "print":
        return "print()"
    if isinstance(node.func, ast.Attribute):
        if node.func.attr == "echo":
            return "click.echo()"
        if node.func.attr == "write" and _is_stream(node.func.value):
            return "sys.stdout.write()"
    return None


def _is_stream(node: ast.expr) -> bool:
    return isinstance(node, ast.Attribute) and node.attr in ("stdout", "stderr")


def main() -> int:
    """Run the check and return the exit status."""
    return report(NAME, findings())


if __name__ == "__main__":
    sys.exit(main())
