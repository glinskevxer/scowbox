"""Check: a migration that has run somewhere is never edited again.

Every book in the field carries a version number, and the program decides what
to do to it by comparing that number with the migrations it knows. Editing
migration four does not change any book that has already run it. It changes
what a fresh book gets, so two books at version nine end up with different
schemas and neither of them is wrong by its own reckoning.

The lock file records what each migration was when it was written. Adding one
appends a line. Changing one is a build failure until somebody deliberately
rewrites the lock, which is the point at which they have to justify it.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from scowbox.store.migrations import MIGRATIONS, Migration
from scowbox.tools.scan import project_root, report

NAME = "check_migrations"
LOCK = "migrations.lock"


def digest(migration: Migration) -> str:
    """A stable hash of everything a migration does."""
    text = "\n".join(statement.strip() for statement in migration.statements)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def lines() -> list[str]:
    """The lock file as it should be, one line per migration."""
    return [f"{m.version:>3} {digest(m)} {m.name}" for m in MIGRATIONS]


def lock_path() -> Path:
    """Where the lock file lives, next to the pyproject."""
    return project_root() / LOCK


def held() -> list[str]:
    """The lock file as it is on disk."""
    where = lock_path()
    if not where.exists():
        return []
    return [line for line in where.read_text(encoding="utf-8").splitlines() if line.strip()]


def findings(wanted: list[str] | None = None, have: list[str] | None = None) -> list[str]:
    """Every migration that has changed, gone missing or arrived unlocked."""
    should = wanted if wanted is not None else lines()
    does = have if have is not None else held()
    if not does:
        return [f"{LOCK} is missing; write it with --write"]
    out = []
    locked = {line.split()[0]: line for line in does}
    written = {line.split()[0]: line for line in should}
    for version, line in sorted(written.items(), key=lambda pair: int(pair[0])):
        if version not in locked:
            out.append(f"migration {version} is not in {LOCK}; write it with --write")
        elif locked[version] != line:
            out.append(f"migration {version} has changed since it was locked")
    for version in sorted(set(locked) - set(written), key=int):
        out.append(f"migration {version} is in {LOCK} and no longer in the code")
    return out


def write() -> Path:
    """Rewrite the lock file from the migrations as they stand."""
    where = lock_path()
    where.write_text("\n".join(lines()) + "\n", encoding="utf-8")
    return where


def main(argv: list[str] | None = None) -> int:
    """Run the check, or rewrite the lock with ``--write``."""
    args = sys.argv[1:] if argv is None else argv
    if "--write" in args:
        print(f"{NAME}: wrote {write()}")
        return 0
    return report(NAME, findings())


if __name__ == "__main__":
    sys.exit(main())
