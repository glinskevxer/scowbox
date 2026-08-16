"""``scowbox report`` prints what the renderers built."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.cli.runner import Book, a_book
from tests.cli.surveying import a_reach, survey_the_reach


@pytest.fixture
def run(tmp_path: Path) -> Book:
    made = a_book(tmp_path)
    made(
        "reach", "add", "RCH-012", "Lower Range",
        "--begin", "100+00", "--end", "140+00",
        "--bottom", "400", "--depth", "42", "--method", "scow",
    )  # fmt: skip
    made("scow", "add", "SC-004", "Dixie 41", "--length", "180", "--width", "42", "--depth", "14")
    made(
        "placement", "add", "PA-002", "Wilmington ODMDS",
        "--ground", "ocean site", "--permit", "SAW-2019-01142",
    )  # fmt: skip
    made(
        "shift", "dredge", "DR-003", "Cherokee",
        "--plant", "mechanical", "--operator", "Norfolk Dredging",
    )  # fmt: skip
    return made


def test_an_empty_day_prints_the_empty_report(run: Book) -> None:
    out = run("report", "day", "--on", "2025-08-06")
    assert "Day report 2025-08-06" in out
    assert "No shift logged." in out


def test_a_day_with_work_prints_it(run: Book) -> None:
    run(
        "shift", "log", "SH-00021",
        "--dredge", "DR-003", "--reach", "RCH-012",
        "--on", "2025-08-06", "--from", "06:00", "--to", "18:00",
    )  # fmt: skip
    run(
        "trip", "add", "TR-04188",
        "--scow", "SC-004", "--reach", "RCH-012",
        "--on", "2025-08-06", "--to", "PA-002",
    )  # fmt: skip
    out = run("report", "day", "--on", "2025-08-06")
    assert "SH-00021" in out
    assert "TR-04188" in out
    assert "no placement ticket" in out


def test_the_reach_report_prints_the_template(run: Book) -> None:
    out = run("report", "reach", "RCH-012")
    assert "Reach RCH-012  Lower Range" in out
    assert "measured by   scow" in out


def test_the_reach_report_on_a_reach_that_is_not_there_fails(run: Book) -> None:
    run("report", "reach", "RCH-999", ok=False)


def test_the_season_report_counts_the_book(run: Book) -> None:
    out = run("report", "season")
    assert "Season report" in out
    assert "reaches       1" in out
    assert "Nothing measured yet." in out


def test_the_season_report_takes_a_material(run: Book) -> None:
    out = run("report", "season", "--material", "clay", "--deduction", "0.1")
    assert "Season report" in out


def test_the_audit_is_clean_on_an_empty_book(run: Book) -> None:
    out = run("report", "audit")
    assert "Audit" in out
    assert "Nothing outstanding." in out


def test_the_audit_finds_a_trip_with_no_ticket(run: Book) -> None:
    run(
        "trip", "add", "TR-04188",
        "--scow", "SC-004", "--reach", "RCH-012",
        "--on", "2025-08-06", "--to", "PA-002",
    )  # fmt: skip
    out = run("report", "audit")
    assert "1 warnings" in out
    assert "no placement ticket" in out


def test_a_closed_month_turns_the_warning_into_a_violation(run: Book) -> None:
    run(
        "trip", "add", "TR-04188",
        "--scow", "SC-004", "--reach", "RCH-012",
        "--on", "2025-08-06", "--to", "PA-002",
    )  # fmt: skip
    out = run("report", "audit", "--closed-through", "2025-08-31")
    assert "1 violations" in out


def test_the_reach_report_takes_a_material_and_a_deduction(run: Book) -> None:
    out = run("report", "reach", "RCH-012", "--material", "sand", "--deduction", "0.15")
    assert "Reach RCH-012" in out


@pytest.fixture
def surveyed(tmp_path: Path) -> Book:
    """A book with one reach measured by a pair of surveys."""
    made = a_book(tmp_path, "surveyed.sqlite3")
    a_reach(made)
    survey_the_reach(made, tmp_path)
    return made


def test_the_section_sheet_prints_the_arithmetic(surveyed: Book) -> None:
    out = surveyed("report", "sections", "RCH-012")
    assert "Sections, RCH-012" in out
    assert "cy removed" in out


def test_the_section_sheet_takes_an_interval(surveyed: Book) -> None:
    out = surveyed("report", "sections", "RCH-012", "--interval", "200")
    assert "sections      3 of 3" in out


def test_the_section_sheet_on_a_reach_with_no_surveys_fails(run: Book) -> None:
    run("report", "sections", "RCH-012", ok=False)


def test_the_production_report_prints(run: Book) -> None:
    out = run("report", "production")
    assert "Production" in out
    assert "average load" in out


def test_the_production_report_narrows_to_a_reach(run: Book) -> None:
    assert "Production, RCH-012" in run("report", "production", "--reach", "RCH-012")


def test_the_fleet_report_prints(run: Book) -> None:
    out = run("report", "fleet")
    assert "Fleet" in out
    assert "DR-003" in out


def test_the_gauge_report_prints(surveyed: Book) -> None:
    out = surveyed("report", "gauges")
    assert "Gauges" in out
    assert "8658120" in out


def test_the_shoaling_report_prints(run: Book) -> None:
    out = run("report", "shoaling")
    assert "Shoaling" in out
    assert "at least 30 days" in out


def test_the_shoaling_report_lists_a_reach_s_intervals(surveyed: Book) -> None:
    out = surveyed("report", "shoaling", "--reach", "RCH-012")
    assert "SV-0031 to SV-0032" in out
    assert "31 days" in out


def test_the_overdepth_report_prints(surveyed: Book) -> None:
    out = surveyed("report", "overdepth")
    assert "Overdepth" in out
    assert "watch above" in out


def test_the_overdepth_report_takes_a_watch(surveyed: Book) -> None:
    assert "50%" in surveyed("report", "overdepth", "--watch", "0.5")


def test_the_closeout_report_prints(surveyed: Book) -> None:
    out = surveyed("report", "closeout")
    assert "Closeout" in out
    assert "outstanding" in out


def test_the_closeout_report_takes_a_closing_day(surveyed: Book) -> None:
    out = surveyed("report", "closeout", "--closed-through", "2025-08-31")
    assert "Closeout" in out


def test_the_estimate_history_prints(surveyed: Book) -> None:
    surveyed(
        "contract", "add", "W912PM-25-C-0014",
        "--awarded", "2025-01-20", "--ntp", "2025-02-03",
        "--days", "730", "--liquidated", "$3,400.00",
    )  # fmt: skip
    surveyed(
        "contract", "item", "LI-0001", "Dredging, base",
        "--unit", "cy", "--price", "$7.35", "--group", "base",
    )  # fmt: skip
    assert "No estimate written yet." in surveyed("report", "estimate")
    surveyed("estimate", "write", "--through", "2025-08-31")
    assert "EST-001" in surveyed("report", "estimate")
    assert "Estimate 1" in surveyed("report", "estimate", "EST-001")
    assert "Line item LI-0001" in surveyed("report", "estimate", "--item", "LI-0001")


def test_the_export_writes_its_files(run: Book, tmp_path: Path) -> None:
    out = run("report", "export", str(tmp_path / "sheets"))
    assert "reaches.csv" in out
    assert (tmp_path / "sheets" / "estimates.csv").exists()


def test_the_window_report_counts_the_workable_days(run: Book) -> None:
    run(
        "window", "add", "loggerhead", "--from", "2026-06-01", "--to", "2026-06-10",
        "--restriction", "closed", "--authority", "NMFS",
    )  # fmt: skip
    out = run("report", "windows", "--from", "2026-06-01", "--to", "2026-06-30")
    assert "Windows 2026-06-01 to 2026-06-30" in out
    assert "workable" in out
    assert "1 windows touch this period" in out


def test_the_window_report_on_a_backwards_period_fails(run: Book) -> None:
    run("report", "windows", "--from", "2026-06-30", "--to", "2026-06-01", ok=False)
