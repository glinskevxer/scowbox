"""The coverage gate, on a report that clears the floors and one that does not."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scowbox.tools.coverage_gate import FileCoverage, findings, main, read


def a_report(tmp_path: Path, overall: float, files: dict[str, float]) -> Path:
    where = tmp_path / "coverage.json"
    where.write_text(
        json.dumps(
            {
                "totals": {"percent_covered": overall},
                "files": {
                    name: {"summary": {"percent_covered": percent, "missing_lines": 3}}
                    for name, percent in files.items()
                },
            }
        ),
        encoding="utf-8",
    )
    return where


def test_a_report_reads_back_worst_first(tmp_path: Path) -> None:
    where = a_report(tmp_path, 96.0, {"a.py": 99.0, "b.py": 80.0})
    overall, files = read(where)
    assert overall == 96.0
    assert [f.name for f in files] == ["b.py", "a.py"]


def test_the_missing_line_count_comes_through(tmp_path: Path) -> None:
    _, files = read(a_report(tmp_path, 96.0, {"a.py": 99.0}))
    assert files[0].missing == 3


def test_a_clean_report_has_no_findings() -> None:
    files = [FileCoverage("a.py", 99.0, 1), FileCoverage("b.py", 90.0, 4)]
    assert findings(96.0, files, 95.0, 85.0) == []


def test_a_package_under_the_floor_is_found() -> None:
    found = findings(90.0, [], 95.0, 85.0)
    assert "coverage is 90.00%, under the 95% floor" in found[0]


def test_a_file_under_the_file_floor_is_found() -> None:
    files = [FileCoverage("b.py", 40.0, 12)]
    found = findings(96.0, files, 95.0, 85.0)
    assert "b.py is 40.00%, under the 85% file floor (12 lines missing)" in found[0]


def test_a_high_package_figure_does_not_hide_a_bad_file() -> None:
    files = [FileCoverage("a.py", 100.0, 0), FileCoverage("b.py", 40.0, 12)]
    assert len(findings(99.0, files, 95.0, 85.0)) == 1


def test_the_real_report_clears_the_floors_when_it_is_there(
    capsys: pytest.CaptureFixture[str],
) -> None:
    try:
        status = main(["--floor", "0", "--file-floor", "0", "--worst", "3"])
    except FileNotFoundError:
        pytest.skip("no coverage report in this run")
    assert status == 0
    assert "coverage_gate" in capsys.readouterr().out
