"""The smoke run, which is one whole job through every layer."""

from __future__ import annotations

import pytest

from scowbox.tools.smoke import main, run


@pytest.fixture(scope="module")
def lines() -> dict[str, str]:
    """One smoke run, read as a mapping. It builds a whole job, so it runs once."""
    return dict(line.split(maxsplit=1) for line in run(quiet=True))


def test_the_smoke_run_finishes() -> None:
    assert main(["--quiet"]) == 0


def test_it_reports_both_measurements_and_the_spread(lines: dict[str, str]) -> None:
    assert lines["survey"].endswith("cy")
    assert lines["scow"].endswith("cy")
    assert lines["spread"].endswith("%")


def test_the_survey_governs_a_job_that_agrees(lines: dict[str, str]) -> None:
    assert lines["governs"] == "survey"
    assert lines["quantity"] == lines["survey"]


def test_the_two_measurements_land_inside_the_tolerance(lines: dict[str, str]) -> None:
    assert float(lines["spread"].rstrip("%")) < 10.0


def test_the_estimate_earns_the_quantity_and_the_lump_sum(lines: dict[str, str]) -> None:
    assert lines["earned"].startswith("$1,")
    assert lines["retained"].startswith("$")
    assert lines["due"].startswith("$")


def test_it_prints_when_it_is_not_quiet(capsys: pytest.CaptureFixture[str]) -> None:
    run(quiet=False)
    out = capsys.readouterr().out
    assert "survey" in out
    assert "due" in out


def test_it_prints_nothing_when_it_is(capsys: pytest.CaptureFixture[str]) -> None:
    run(quiet=True)
    assert capsys.readouterr().out == ""
