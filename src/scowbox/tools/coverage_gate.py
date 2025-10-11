"""Check: the coverage report clears the floors.

Two floors, not one. A whole package figure hides a module at forty percent
behind twenty modules at ninety nine, and the module at forty percent is
usually the one that was added last and is about to be relied on.

So there is a floor for the package and a lower floor every individual file has
to clear on its own, and the worst few are printed whether the gate passes or
not, because the useful reading is which files are worst, not whether today's
number is above a line.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from scowbox.tools.scan import project_root

NAME = "coverage_gate"
REPORT = "coverage.json"


@dataclass(frozen=True)
class FileCoverage:
    """One file's figure out of the coverage report."""

    name: str
    percent: float
    missing: int


def read(path: Path | None = None) -> tuple[float, list[FileCoverage]]:
    """The package figure and every file's figure, worst first."""
    where = path or project_root() / REPORT
    held = json.loads(where.read_text(encoding="utf-8"))
    overall = float(held["totals"]["percent_covered"])
    files = [
        FileCoverage(
            name=name,
            percent=float(body["summary"]["percent_covered"]),
            missing=int(body["summary"]["missing_lines"]),
        )
        for name, body in held["files"].items()
    ]
    files.sort(key=lambda f: (f.percent, f.name))
    return overall, files


def findings(
    overall: float, files: list[FileCoverage], floor: float, file_floor: float
) -> list[str]:
    """Every floor the report does not clear."""
    out = []
    if overall < floor:
        out.append(f"coverage is {overall:.2f}%, under the {floor:.0f}% floor")
    out.extend(
        f"{one.name} is {one.percent:.2f}%, under the {file_floor:.0f}% file floor"
        f" ({one.missing} lines missing)"
        for one in files
        if one.percent < file_floor
    )
    return out


def _number(args: list[str], flag: str, fallback: float) -> float:
    if flag not in args:
        return fallback
    return float(args[args.index(flag) + 1])


def main(argv: list[str] | None = None) -> int:
    """Read the report and hold it to the floors."""
    args = sys.argv[1:] if argv is None else argv
    floor = _number(args, "--floor", 95.0)
    file_floor = _number(args, "--file-floor", 85.0)
    worst = int(_number(args, "--worst", 5))
    overall, files = read()
    print(f"{NAME}: {overall:.2f}% over {len(files)} files")
    for one in files[:worst]:
        print(f"  {one.percent:6.2f}%  {one.missing:>4} missing  {one.name}")
    found = findings(overall, files, floor, file_floor)
    for finding in found:
        print(f"  {finding}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
