"""Finding and parsing this package's own source.

Every check starts from the same two questions: which files am I looking at,
and what is in them. Both answers live here so that a check added later cannot
quietly disagree with the others about whether the tests count.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

PACKAGE = "scowbox"


def package_root() -> Path:
    """The directory holding the installed package's source."""
    import scowbox

    return Path(str(scowbox.__file__)).resolve().parent


def project_root() -> Path:
    """The checkout, found by walking up from the package to the pyproject."""
    here = package_root()
    for candidate in [here, *here.parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise FileNotFoundError("no pyproject.toml above the package")


def source_files(root: Path | None = None) -> list[Path]:
    """Every module of the package, in a stable order."""
    where = root or package_root()
    return sorted(p for p in where.rglob("*.py") if "__pycache__" not in p.parts)


def suite_files() -> list[Path]:
    """Every test module, in a stable order.

    Not called ``test_files``. Pytest collects anything named ``test_*`` that a
    test module imports, so a helper with that name is run as a test, passes
    trivially, and then starts failing on a warning about returning a value.
    """
    where = project_root() / "tests"
    if not where.is_dir():
        return []
    return sorted(p for p in where.rglob("test_*.py") if "__pycache__" not in p.parts)


def module_name(path: Path, root: Path | None = None) -> str:
    """The dotted name a source file is imported under."""
    where = root or package_root()
    parts = path.relative_to(where).with_suffix("").parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join((PACKAGE, *parts))


@dataclass(frozen=True)
class Module:
    """One parsed source file."""

    path: Path
    name: str
    tree: ast.Module

    @property
    def where(self) -> str:
        """A short path for a finding, relative to the package."""
        return self.name

    def functions(self) -> Iterator[ast.FunctionDef]:
        """Every module level function, private ones included."""
        for node in self.tree.body:
            if isinstance(node, ast.FunctionDef):
                yield node

    def classes(self) -> Iterator[ast.ClassDef]:
        for node in self.tree.body:
            if isinstance(node, ast.ClassDef):
                yield node

    def imports(self) -> Iterator[str]:
        """Every module of this package that this one imports."""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(PACKAGE):
                        yield alias.name
            elif (
                isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(PACKAGE)
            ):
                yield node.module


def parse(path: Path, root: Path | None = None) -> Module:
    """Read and parse one source file."""
    return Module(
        path=path,
        name=module_name(path, root),
        tree=ast.parse(path.read_text(encoding="utf-8"), filename=str(path)),
    )


def modules(root: Path | None = None) -> list[Module]:
    """Every module of the package, parsed."""
    where = root or package_root()
    return [parse(path, where) for path in source_files(where)]


def report(name: str, findings: list[str]) -> int:
    """Print what a check found and return the status it should exit with."""
    if not findings:
        print(f"{name}: nothing to report")
        return 0
    print(f"{name}: {len(findings)} findings")
    for finding in findings:
        print(f"  {finding}")
    return 1
