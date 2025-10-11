"""Check: CI runs every check, and the walk types real commands.

A check nobody runs is a comment. Adding one to this package and forgetting to
add its line to the workflow leaves a tool that passes on the machine it was
written on and is never run again, which is worse than not having written it.

The walk is checked the other way round. It is a shell script inside a YAML
file, so nothing about it is validated until it runs, and a command renamed
here turns into a red build for a reason that has nothing to do with the change
that caused it. Every command word in the walk is resolved against the real
command tree before CI ever sees it.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import click

from scowbox.cli.main import cli
from scowbox.tools.scan import package_root, project_root, report

NAME = "check_workflow"
WORKFLOW = ".github/workflows/ci.yml"
GENERATORS = ("schema_dump", "build_docs")
INVOCATION = re.compile(r"\bscowbox --book \"\$book\" ([^\n|]*)")


def workflow_path() -> Path:
    """Where the workflow lives."""
    return project_root() / WORKFLOW


def workflow_text() -> str:
    """The workflow as text. It is checked as text, not parsed as YAML."""
    return workflow_path().read_text(encoding="utf-8")


def check_tools() -> list[str]:
    """Every check tool the package holds."""
    where = package_root() / "tools"
    return sorted(path.stem for path in where.glob("check_*.py") if path.name != "__init__.py")


def resolve(words: list[str]) -> str | None:
    """Follow a list of words down the tree, naming the first that is not there.

    Walking stops at a leaf. A group takes no arguments, so a word a group does
    not know is a finding; a word after a leaf command is an argument to it and
    is none of this check's business.
    """
    command: click.Command = cli
    for word in words:
        if not isinstance(command, click.Group):
            return None
        found = command.commands.get(word)
        if found is None:
            return word
        command = found
    return None


def invocations(text: str) -> list[list[str]]:
    """The command words of every walk line, options and arguments dropped."""
    out = []
    for line in INVOCATION.findall(text):
        words: list[str] = []
        for word in line.split():
            if word.startswith("-"):
                break
            words.append(word)
        if words:
            out.append(words)
    return out


def findings(text: str | None = None, tools: list[str] | None = None) -> list[str]:
    """Every check missing from CI and every walk command that does not exist."""
    held = workflow_text() if text is None else text
    out = []
    for tool in tools if tools is not None else check_tools():
        if f"scowbox.tools.{tool}" not in held:
            out.append(f"{tool} is not run by {WORKFLOW}")
    for generator in GENERATORS:
        if f"scowbox.tools.{generator} --check" not in held:
            out.append(f"{generator} is not run with --check by {WORKFLOW}")
    for words in invocations(held):
        missing = resolve(words)
        if missing is not None:
            out.append(f"the walk types {' '.join(words)!r}, and {missing!r} is not a command")
    return out


def main() -> int:
    """Run the check and return the exit status."""
    return report(NAME, findings())


if __name__ == "__main__":
    sys.exit(main())
