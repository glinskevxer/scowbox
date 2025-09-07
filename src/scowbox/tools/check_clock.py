"""Check: nothing in the package asks the machine what time it is.

Every date this program works with is a date somebody wrote on a piece of
paper. The day a shift was worked, the day a survey was run, the day an
estimate runs through. None of them is today, and the two places that briefly
used today were both wrong: an estimate built on Monday for the month ending
Sunday, and a window check that read a closure as open because the test ran in
December.

So the operating date is an argument, always, and a call to ``now`` anywhere in
the package is a finding.
"""

from __future__ import annotations

import ast
import sys

from scowbox.tools.scan import Module, modules, report

NAME = "check_clock"

FORBIDDEN = {
    "now": "datetime.now",
    "today": "date.today",
    "utcnow": "datetime.utcnow",
    "time": "time.time",
    "monotonic": "time.monotonic",
}
ALLOWED_MODULES = ("scowbox.tools.",)


def findings(found: list[Module] | None = None) -> list[str]:
    """Every call that reads the wall clock."""
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
        name = _called(node)
        if name in FORBIDDEN:
            out.append(
                f"{module.where} line {node.lineno} calls {name}(), which reads the wall clock"
            )
    return out


def _called(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    if isinstance(node.func, ast.Name):
        return node.func.id
    return None


def main() -> int:
    """Run the check and return the exit status."""
    return report(NAME, findings())


if __name__ == "__main__":
    sys.exit(main())
