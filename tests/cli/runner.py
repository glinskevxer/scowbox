"""One runner bound to one book.

Six command line suites had written this out, and the copies had already drifted
in the part that matters: two of them asserted the exit status and printed the
output on failure, three asserted only the status, and one asserted nothing at
all, so a command that had started failing there passed for a fortnight.
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from scowbox.cli.main import cli


class Book:
    """A command line bound to one book file."""

    def __init__(self, path: Path) -> None:
        self.path = str(path)
        self.runner = CliRunner()

    def __call__(self, *args: str, ok: bool = True) -> str:
        """Run a command and assert whether it was meant to work."""
        result = self.runner.invoke(cli, ["--book", self.path, *args], obj={})
        if ok:
            assert result.exit_code == 0, result.output + str(result.exception)
        else:
            assert result.exit_code != 0, f"expected a failure, got: {result.output}"
        return result.output


def a_book(tmp_path: Path, name: str = "book.sqlite3") -> Book:
    """A fresh book with the schema on it."""
    made = Book(tmp_path / name)
    made("init")
    return made
