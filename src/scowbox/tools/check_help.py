"""Check: every command and every option says what it does.

The command line is the whole interface. A project engineer working out how to
log a scow trip reads ``--help`` and nothing else, so an option with no help
text is an option nobody outside this room can use.

The check walks the real command tree rather than the source, because that is
what a user meets. A command hung on the group in a way the source does not
make obvious is still checked, and one that is defined and never hung on
anything is caught by the count.
"""

from __future__ import annotations

import sys

import click

from scowbox.cli.main import cli
from scowbox.tools.scan import report

NAME = "check_help"
MIN_WORDS = 3


def walk(command: click.Command, path: str = "") -> list[tuple[str, click.Command]]:
    """Every command in the tree, with the words a user would type to reach it."""
    here = f"{path} {command.name}".strip()
    found = [(here, command)]
    if isinstance(command, click.Group):
        for name in sorted(command.commands):
            found.extend(walk(command.commands[name], here))
    return found


def findings(root: click.Command | None = None) -> list[str]:
    """Every command or option that does not say what it is for."""
    out = []
    for path, command in walk(root or cli):
        text = (command.help or command.short_help or "").strip()
        if not text:
            out.append(f"{path} has no help")
        elif len(text.split()) < MIN_WORDS:
            out.append(f"{path} has help of under {MIN_WORDS} words")
        for parameter in command.params:
            out.extend(_parameter(path, parameter))
    return out


def _parameter(path: str, parameter: click.Parameter) -> list[str]:
    if not isinstance(parameter, click.Option):
        return []
    if parameter.name in ("help", "version"):
        return []
    if not (parameter.help or "").strip():
        return [f"{path} option --{parameter.name} has no help"]
    return []


def commands() -> int:
    """How many commands the tree holds, top level group included."""
    return len(walk(cli))


def main() -> int:
    """Run the check and return the exit status."""
    return report(NAME, findings())


if __name__ == "__main__":
    sys.exit(main())
