"""Check: the README types commands that work.

A README is the one document everybody reads and the one nobody runs. The
example in it is copied into a terminal by somebody on their first afternoon,
and an option renamed two releases ago costs them twenty minutes and most of
their patience.

So every command word in the README is resolved against the real command tree,
every long option is checked against the command it is written under, and every
file the README points at has to be there.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import click

from scowbox.cli.main import cli
from scowbox.tools.check_workflow import resolve
from scowbox.tools.scan import project_root, report

NAME = "check_readme"
DOCUMENT = "README.md"
INVOCATION = re.compile(r"^\s*scowbox (.+?)(\\)?$", re.MULTILINE)
POINTED_AT = re.compile(r"`(docs/[A-Za-z0-9_./-]+)`")


def readme_path() -> Path:
    """Where the README lives."""
    return project_root() / DOCUMENT


def readme_text() -> str:
    """The README as text."""
    return readme_path().read_text(encoding="utf-8")


def invocations(text: str) -> list[list[str]]:
    """The whole of every command line the README types, options included."""
    return [line.split() for line, _ in INVOCATION.findall(text)]


def words(invocation: list[str]) -> list[str]:
    """The command words of an invocation, options and their values dropped."""
    found = []
    skip = 0
    for index, word in enumerate(invocation):
        if skip:
            skip -= 1
            continue
        if word.startswith("-"):
            if word == "--book":
                skip = 1
            continue
        if index and invocation[index - 1].startswith("-"):
            continue
        found.append(word)
    return found


def options(invocation: list[str]) -> list[str]:
    """Every long option the invocation passes."""
    return [word for word in invocation if word.startswith("--")]


def known(path: list[str]) -> set[str]:
    """Every long option the command at this path takes, the group's included."""
    command: click.Command = cli
    found = {f"--{p.name}" for p in cli.params if isinstance(p, click.Option)}
    found.update({"--book", "--help", "--version"})
    for word in path:
        if not isinstance(command, click.Group):
            break
        nested = command.commands.get(word)
        if nested is None:
            return found
        command = nested
        found.update(opt for p in command.params if isinstance(p, click.Option) for opt in p.opts)
    return found


def findings(text: str | None = None) -> list[str]:
    """Every command, option or file the README names that is not there."""
    held = readme_text() if text is None else text
    out = []
    for invocation in invocations(held):
        path = words(invocation)
        missing = resolve(path)
        if missing is not None:
            out.append(f"the README types {' '.join(path)!r}, and {missing!r} is not a command")
            continue
        allowed = known(path)
        out.extend(
            f"the README passes {option} to {' '.join(path)!r}, which does not take it"
            for option in options(invocation)
            if option not in allowed
        )
    out.extend(
        f"the README points at {where}, which is not there"
        for where in POINTED_AT.findall(held)
        if not (project_root() / where).exists()
    )
    return out


def main() -> int:
    """Run the check and return the exit status."""
    return report(NAME, findings())


if __name__ == "__main__":
    sys.exit(main())
