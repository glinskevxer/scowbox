"""The fixture check, on this suite and on a fixture that leaks."""

from __future__ import annotations

from pathlib import Path

import pytest

from scowbox.tools.check_fixtures import findings, is_fixture, main, opens


def a_suite(tmp_path: Path, body: str) -> list[str]:
    where = tmp_path / "test_sample.py"
    where.write_text('"""A sample suite."""\n' + body, encoding="utf-8")
    return findings([where])


def test_this_suite_has_nothing_to_report() -> None:
    assert findings() == []


def test_the_check_exits_clean(capsys: pytest.CaptureFixture[str]) -> None:
    assert main() == 0
    assert "check_fixtures" in capsys.readouterr().out


def test_a_fixture_that_returns_an_open_book_is_found(tmp_path: Path) -> None:
    found = a_suite(
        tmp_path,
        "import pytest\n\n\n@pytest.fixture\ndef open_book(tmp_path):\n"
        "    return book(tmp_path / 'b.sqlite3', create=True)\n",
    )
    assert found == ["test_sample.py::open_book calls book() and never closes it"]


def test_a_fixture_that_yields_inside_a_with_is_fine(tmp_path: Path) -> None:
    found = a_suite(
        tmp_path,
        "import pytest\n\n\n@pytest.fixture\ndef open_book(tmp_path):\n"
        "    with book(tmp_path / 'b.sqlite3', create=True) as connection:\n"
        "        yield connection\n",
    )
    assert found == []


def test_a_fixture_that_opens_nothing_is_fine(tmp_path: Path) -> None:
    found = a_suite(tmp_path, "import pytest\n\n\n@pytest.fixture\ndef a_reach():\n    return 1\n")
    assert found == []


def test_a_plain_function_that_opens_is_not_a_fixture(tmp_path: Path) -> None:
    found = a_suite(tmp_path, "def helper(tmp_path):\n    return book(tmp_path, create=True)\n")
    assert found == []


def test_a_temporary_directory_counts_as_an_opener(tmp_path: Path) -> None:
    found = a_suite(
        tmp_path,
        "import pytest\nimport tempfile\n\n\n@pytest.fixture\ndef somewhere():\n"
        "    return tempfile.TemporaryDirectory()\n",
    )
    assert "TemporaryDirectory()" in found[0]


def test_a_decorated_fixture_with_arguments_is_seen(tmp_path: Path) -> None:
    found = a_suite(
        tmp_path,
        "import pytest\n\n\n@pytest.fixture(scope='module')\ndef open_book(tmp_path):\n"
        "    return book(tmp_path, create=True)\n",
    )
    assert len(found) == 1


def test_the_openers_a_fixture_calls_come_back_in_order() -> None:
    import ast

    tree = ast.parse(
        "import pytest\n\n\n@pytest.fixture\ndef f():\n    return connect(book('x'))\n"
    )
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
    assert is_fixture(node)
    assert opens(node) == ["connect", "book"]
