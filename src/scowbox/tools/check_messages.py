"""Check: the errors read the same way as each other.

An error from this package ends up on a terminal after a colon, next to a code:
``rule: RCH-012 is measured by scow, not by survey``. That is a sentence
fragment and it is meant to be, so it starts lower case and it does not end in
a full stop. One that does neither reads as though two programs are talking.

The check is on the literal parts of the message, so anything interpolated is
skipped: a message that starts with a reach identifier is starting with a
capital and is right to.
"""

from __future__ import annotations

import ast
import sys

from scowbox.tools.scan import Module, modules, report

NAME = "check_messages"
ERRORS = (
    "ScowboxError",
    "InputError",
    "FieldError",
    "RangeError",
    "MissingError",
    "DuplicateError",
    "StateError",
    "RuleError",
)
CARRIES_MESSAGE = {"ScowboxError": 0, "InputError": 0, "StateError": 0, "RuleError": 0}


def messages(module: Module) -> list[tuple[int, str]]:
    """Every literal message this module raises, with its line."""
    found = []
    for node in ast.walk(module.tree):
        if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
            continue
        called = node.exc.func
        name = called.id if isinstance(called, ast.Name) else None
        if name not in ERRORS:
            continue
        at = CARRIES_MESSAGE.get(name, 1)
        if len(node.exc.args) <= at:
            continue
        text = _literal(node.exc.args[at])
        if text is not None:
            found.append((node.lineno, text))
    return found


def _literal(node: ast.expr) -> str | None:
    """The literal head of a message, or nothing where it starts interpolated."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        pieces = [p for p in node.values if isinstance(p, ast.Constant)]
        if not pieces or node.values[0] is not pieces[0]:
            return None
        return "".join(str(p.value) for p in pieces)
    return None


def _capitalised(head: str) -> bool:
    """True when the first word is an ordinary word written with a capital.

    An identifier is not. ``RCH-012`` starts a message with a capital and is
    right to, and so does ``USACE``; only a word that is otherwise lower case
    reads as a sentence somebody started.
    """
    return head.isalpha() and head[:1].isupper() and head[1:].islower()


def findings(found: list[Module] | None = None) -> list[str]:
    """Every message that does not read like the others."""
    out = []
    for module in found if found is not None else modules():
        for line, text in messages(module):
            trimmed = text.strip()
            if not trimmed:
                out.append(f"{module.where} line {line} raises an empty message")
                continue
            if trimmed.endswith("."):
                out.append(f"{module.where} line {line} ends in a full stop: {trimmed!r}")
            if _capitalised(trimmed.split()[0]):
                out.append(f"{module.where} line {line} starts capitalised: {trimmed!r}")
    return out


def main() -> int:
    """Run the check and return the exit status."""
    return report(NAME, findings())


if __name__ == "__main__":
    sys.exit(main())
