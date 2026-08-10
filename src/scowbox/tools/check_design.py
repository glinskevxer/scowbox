"""Check: the design note names code that exists.

A design document is the first thing to go stale and the last thing anybody
notices has. It survives three renames and then it is actively misleading,
which is worse than not having one.

So the note names things in backticks, and every dotted name in backticks has
to resolve: a module of this package, or an attribute of one. Prose is left
alone, and so is anything in backticks that is not dotted, because that is a
command or a column and this check has no business with those.

The standing rules in `scowbox.laws` are checked the same way, and for the same
reason. Each of them names the module that enforces it, and a rule pointing at
a module that has gone is a rule nobody is enforcing.
"""

from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path

from scowbox.laws import LAWS
from scowbox.tools.scan import PACKAGE, project_root, report

NAME = "check_design"
DOCUMENT = "docs/design.md"
QUOTED = re.compile(r"`([A-Za-z_][A-Za-z0-9_.]*)`")


def document_path() -> Path:
    """Where the design note lives."""
    return project_root() / DOCUMENT


def named(text: str | None = None) -> list[str]:
    """Every dotted name of this package the note mentions, in order, once each."""
    held = text if text is not None else document_path().read_text(encoding="utf-8")
    found = []
    for name in QUOTED.findall(held):
        if "." in name and name.split(".")[0] == PACKAGE and name not in found:
            found.append(name)
    return found


def resolves(name: str) -> bool:
    """True when the dotted name is a module of the package or an attribute of one."""
    try:
        importlib.import_module(name)
    except ImportError:
        pass
    else:
        return True
    holder, _, attribute = name.rpartition(".")
    try:
        module = importlib.import_module(holder)
    except ImportError:
        return False
    return hasattr(module, attribute)


def findings(text: str | None = None) -> list[str]:
    """Every name the note or the standing rules mention that is not there."""
    where = document_path()
    if text is None and not where.exists():
        return [f"{DOCUMENT} is missing"]
    out = [
        f"{DOCUMENT} names {name}, which is not there" for name in named(text) if not resolves(name)
    ]
    out.extend(
        f"the {law.subject} law names {law.where}, which is not there"
        for law in LAWS
        if not resolves(law.where)
    )
    return out


def unlawed() -> list[str]:
    """Standing rules whose module the design note never mentions.

    Not a finding. A law can live in a module the note does not walk through,
    and several do. It is here because the two documents drifting apart is the
    thing worth looking at once a year, and nobody looks at what nothing prints.
    """
    walked = set(named())
    return sorted({law.where for law in LAWS} - walked)


def main() -> int:
    """Run the check and return the exit status."""
    return report(NAME, findings())


if __name__ == "__main__":
    sys.exit(main())
