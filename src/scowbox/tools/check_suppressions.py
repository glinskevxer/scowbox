"""Check: nothing in the package silences a checker.

The comments that turn a lint rule or a type error off are perfectly reasonable
tools, and in a package this size they are a way of shipping a finding with a
note attached. Four of the five that were here turned out to be a missing type
parameter somebody could have written in thirty seconds, and the fifth was a
bare except catching a keyboard interrupt on the way past.

The tests are a different matter. A test that deliberately builds a bad record
has to tell the type checker so, and those are left alone: only the package
itself is swept. The patterns live in MARKS, spelled out there rather than in
this docstring so that the check does not report itself.
"""

from __future__ import annotations

import re
import sys

from scowbox.tools.scan import package_root, report, source_files

NAME = "check_suppressions"
MARKS = (
    re.compile(r"#\s*noqa"),
    re.compile(r"#\s*type:\s*ignore"),
    re.compile(r"#\s*mypy:\s*ignore"),
    re.compile(r"#\s*pragma:\s*no\s*cover"),
)


def findings() -> list[str]:
    """Every line in the package that silences a checker."""
    where = package_root()
    out = []
    for path in source_files(where):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for mark in MARKS:
                if mark.search(line):
                    out.append(f"{path.relative_to(where)} line {number}: {line.strip()[-60:]}")
                    break
    return out


def main() -> int:
    """Run the check and return the exit status."""
    return report(NAME, findings())


if __name__ == "__main__":
    sys.exit(main())
