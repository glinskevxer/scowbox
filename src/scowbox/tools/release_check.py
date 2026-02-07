"""Check: the version is one number, written in three places that agree.

``scowbox.__version__``, the version in the project file and the top entry of
the changelog. Three copies is two too many and there is no way round it: the
package needs the version at runtime, the build backend needs it before the
package is importable, and the changelog is written by a person.

So the number is not deduplicated; it is checked. The check is cheap and it
fires on exactly the release where somebody bumped two of the three.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from scowbox import __version__
from scowbox.tools.scan import project_root, report

NAME = "release_check"
CHANGELOG = "CHANGELOG.md"
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
PROJECT_VERSION = re.compile(r'^version = "([^"]+)"$', re.MULTILINE)
ENTRY = re.compile(r"^## (\d+\.\d+\.\d+)", re.MULTILINE)


def changelog_path() -> Path:
    """Where the changelog lives."""
    return project_root() / CHANGELOG


def project_version(text: str | None = None) -> str | None:
    """The version the build backend will use."""
    held = text or (project_root() / "pyproject.toml").read_text(encoding="utf-8")
    match = PROJECT_VERSION.search(held)
    return match.group(1) if match else None


def entries(text: str | None = None) -> list[str]:
    """Every version the changelog has an entry for, newest first."""
    held = text or changelog_path().read_text(encoding="utf-8")
    return ENTRY.findall(held)


def findings(package: str | None = None) -> list[str]:
    """Every place the three copies of the version disagree."""
    version = package or __version__
    out = []
    if not SEMVER.match(version):
        out.append(f"{version!r} is not a three part version")
    declared = project_version()
    if declared != version:
        out.append(f"the package says {version} and pyproject.toml says {declared}")
    if not changelog_path().exists():
        out.append(f"{CHANGELOG} is missing")
        return out
    written = entries()
    if not written:
        out.append(f"{CHANGELOG} has no version entries")
    elif written[0] != version:
        out.append(f"the package says {version} and the top of {CHANGELOG} says {written[0]}")
    if len(set(written)) != len(written):
        out.append(f"{CHANGELOG} has the same version twice")
    return out


def main() -> int:
    """Run the check and return the exit status."""
    return report(NAME, findings())


if __name__ == "__main__":
    sys.exit(main())
