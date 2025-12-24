"""Check: every dependency is pinned, and the closure is written down.

A range is a promise that the next release of somebody else's package will not
break this one, and nobody is in a position to make that promise. So every
dependency here is pinned to an exact version, and the transitive closure is
pinned too, in a constraints file CI installs against.

The check is text on both files rather than a resolver run. It cannot tell
whether the closure is complete; what it can tell is whether a direct pin is
missing from it, and that is the failure that actually happens, on the day
somebody adds a package to the project and not to the constraints.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from scowbox.tools.scan import project_root, report

NAME = "check_pins"
PINNED = re.compile(r'^"?([A-Za-z0-9_.\-]+)==([0-9][^"\s]*)"?,?$')
REQUIREMENT = re.compile(r'"([A-Za-z0-9_.\-]+)([^"]*)"')
BLOCKS = ("dependencies = [", "dev = [")


def pyproject_text() -> str:
    """The project file as text."""
    return (project_root() / "pyproject.toml").read_text(encoding="utf-8")


def constraints_text() -> str:
    """The constraints file as text."""
    return (project_root() / "constraints.txt").read_text(encoding="utf-8")


def declared(text: str) -> list[tuple[str, str]]:
    """Every dependency named in the project file, with what follows its name.

    The two lists are found by their key and read to the closing bracket, which
    handles both shapes the file uses: one on a line, and one per line. A line
    based reader missed the single line form entirely and reported the direct
    dependency as absent from a file it was sitting in.
    """
    found: list[tuple[str, str]] = []
    for key in BLOCKS:
        at = text.find(key)
        while at != -1:
            end = text.find("]", at)
            inside = text[at + len(key) : end if end != -1 else len(text)]
            found.extend((match.group(1), match.group(2)) for match in REQUIREMENT.finditer(inside))
            at = text.find(key, at + 1)
    return found


def constrained(text: str) -> dict[str, str]:
    """Every pin in the constraints file."""
    found = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = PINNED.match(stripped)
        if match:
            found[match.group(1).lower().replace("_", "-")] = match.group(2)
    return found


def findings(project: str | None = None, closure: str | None = None) -> list[str]:
    """Every dependency that is not pinned, or pinned in only one of the two."""
    wanted = declared(pyproject_text() if project is None else project)
    have = constrained(constraints_text() if closure is None else closure)
    out = []
    for name, rest in wanted:
        key = name.lower().replace("_", "-")
        if not rest.startswith("=="):
            out.append(f"{name} is declared as {name}{rest}, which is not an exact pin")
            continue
        version = rest.removeprefix("==")
        if key not in have:
            out.append(f"{name} is pinned in pyproject.toml and missing from constraints.txt")
        elif have[key] != version:
            out.append(f"{name} is {version} in pyproject.toml and {have[key]} in constraints.txt")
    return out


def lock_paths() -> tuple[Path, Path]:
    """The two files this check compares."""
    return project_root() / "pyproject.toml", project_root() / "constraints.txt"


def main() -> int:
    """Run the check and return the exit status."""
    return report(NAME, findings())


if __name__ == "__main__":
    sys.exit(main())
