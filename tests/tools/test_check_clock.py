"""The clock check, on this package and on a call that reads the clock."""

from __future__ import annotations

from pathlib import Path

import pytest

from scowbox.tools.check_clock import findings, main
from scowbox.tools.scan import parse


def a_module(tmp_path: Path, body: str, package: str = "job") -> list[str]:
    where = tmp_path / package
    where.mkdir(exist_ok=True)
    module = where / "sample.py"
    module.write_text('"""A sample module for the check."""\n' + body, encoding="utf-8")
    return findings([parse(module, tmp_path)])


def test_this_package_passes() -> None:
    assert findings() == []


def test_the_check_exits_clean(capsys: pytest.CaptureFixture[str]) -> None:
    assert main() == 0
    assert "check_clock" in capsys.readouterr().out


def test_a_call_to_now_is_found(tmp_path: Path) -> None:
    found = a_module(tmp_path, "import datetime as dt\n\nx = dt.datetime.now()\n")
    assert "calls now()" in found[0]


def test_a_call_to_today_is_found(tmp_path: Path) -> None:
    found = a_module(tmp_path, "import datetime as dt\n\nx = dt.date.today()\n")
    assert "calls today()" in found[0]


def test_a_bare_call_to_a_forbidden_name_is_found(tmp_path: Path) -> None:
    found = a_module(tmp_path, "from time import time\n\nx = time()\n")
    assert "calls time()" in found[0]


def test_the_line_number_is_reported(tmp_path: Path) -> None:
    found = a_module(tmp_path, "import datetime as dt\n\n\nx = dt.date.today()\n")
    assert "line 5" in found[0]


def test_a_date_passed_in_is_fine(tmp_path: Path) -> None:
    found = a_module(
        tmp_path,
        "import datetime as dt\n\n\ndef go(day: dt.date) -> dt.date:\n    return day\n",
    )
    assert found == []


def test_the_check_tools_are_allowed_a_clock(tmp_path: Path) -> None:
    found = a_module(tmp_path, "import datetime as dt\n\nx = dt.date.today()\n", "tools")
    assert found == []
