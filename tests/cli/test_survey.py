"""``scowbox survey`` through a real book and a real export file."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.cli.runner import Book, a_book


@pytest.fixture
def run(tmp_path: Path) -> Book:
    made = a_book(tmp_path)
    made(
        "reach", "add", "RCH-012", "Lower Range",
        "--begin", "100+00", "--end", "140+00",
        "--bottom", "400", "--depth", "42", "--advance", "2", "--overdepth", "2",
    )  # fmt: skip
    made(
        "survey", "add", "SV-0031", "RCH-012",
        "--kind", "before", "--on", "2025-03-14",
        "--vessel", "Cape Fear", "--draft", "2.5", "--gauge", "8658120",
    )  # fmt: skip
    return made


def an_export(where: Path, *rows: str) -> str:
    where.write_text("station,offset,depth,time\n" + "\n".join(rows) + "\n", encoding="utf-8")
    return str(where)


def test_an_added_survey_shows_up(run: Book) -> None:
    assert "SV-0031" in run("survey", "list")


def test_an_empty_book_says_so(tmp_path: Path) -> None:
    fresh = a_book(tmp_path, "empty.sqlite3")
    assert "no surveys" in fresh("survey", "list")


def test_a_survey_of_a_reach_that_is_not_there_is_refused(run: Book) -> None:
    run(
        "survey", "add", "SV-0099", "RCH-999",
        "--kind", "before", "--on", "2025-03-14",
        "--vessel", "Cape Fear", "--draft", "2.5", ok=False,
    )  # fmt: skip


def test_loading_reports_what_went_in(run: Book, tmp_path: Path) -> None:
    export = an_export(tmp_path / "shots.csv", "100+00,-50,41.2,07:45", "100+00,50,43.8,07:45")
    out = run("survey", "load", "SV-0031", export)
    assert "2 shots loaded, 0 replaced" in out


def test_loading_twice_replaces_the_shots(run: Book, tmp_path: Path) -> None:
    export = an_export(tmp_path / "shots.csv", "100+00,-50,41.2,07:45", "100+00,50,43.8,07:45")
    run("survey", "load", "SV-0031", export)
    assert "2 shots loaded, 2 replaced" in run("survey", "load", "SV-0031", export)


def test_bad_lines_are_counted(run: Book, tmp_path: Path) -> None:
    export = an_export(tmp_path / "shots.csv", "100+00,-50,41.2,07:45", "wrong,0,0,07:45")
    out = run("survey", "load", "SV-0031", export)
    assert "1 lines would not read" in out


def test_bad_lines_can_be_listed(run: Book, tmp_path: Path) -> None:
    export = an_export(tmp_path / "shots.csv", "wrong,0,0,07:45")
    out = run("survey", "load", "SV-0031", export, "--show-refused")
    assert "line 2:" in out


def test_show_counts_the_shots_and_the_stations(run: Book, tmp_path: Path) -> None:
    export = an_export(
        tmp_path / "shots.csv",
        "100+00,-50,41.2,07:45",
        "100+00,50,43.8,07:45",
        "101+00,0,42.0,07:50",
    )
    run("survey", "load", "SV-0031", export)
    out = run("survey", "show", "SV-0031")
    assert "soundings  3" in out
    assert "2 from 100+00 to 101+00" in out
    assert "pays       yes" in out


def test_a_named_gauge_shows_on_the_survey(run: Book) -> None:
    assert "gauge      8658120" in run("survey", "show", "SV-0031")


def test_a_survey_with_no_gauge_says_so(run: Book) -> None:
    run(
        "survey", "add", "SV-0033", "RCH-012",
        "--kind", "sweep", "--on", "2025-03-21",
        "--vessel", "Cape Fear", "--draft", "2.5",
    )  # fmt: skip
    assert "gauge      none named" in run("survey", "show", "SV-0033")


def test_a_progress_survey_does_not_pay(run: Book) -> None:
    run(
        "survey", "add", "SV-0032", "RCH-012",
        "--kind", "progress", "--on", "2025-03-20",
        "--vessel", "Cape Fear", "--draft", "2.5",
    )  # fmt: skip
    assert "pays       no" in run("survey", "show", "SV-0032")


def test_the_reach_filter_narrows_the_list(run: Book) -> None:
    assert "SV-0031" in run("survey", "list", "--reach", "RCH-012")
    assert "no surveys" in run("survey", "list", "--reach", "RCH-999")


def test_loading_into_a_survey_that_is_not_there_fails(run: Book, tmp_path: Path) -> None:
    export = an_export(tmp_path / "shots.csv", "100+00,-50,41.2,07:45")
    run("survey", "load", "SV-0099", export, ok=False)


def test_a_clean_survey_checks_sound(run: Book, tmp_path: Path) -> None:
    where = tmp_path / "gauge.csv"
    where.write_text(
        "Date Time,Water Level,Quality\n2025-03-14 06:54,2.000,v\n2025-03-14 07:06,2.000,v\n",
        encoding="utf-8",
    )
    run("tide", "load", "8658120", str(where))
    shots = an_export(
        tmp_path / "shots.csv",
        "100+00,-200,41.2,07:00",
        "100+00,0,41.2,07:00",
        "100+00,200,41.2,07:00",
    )
    run("survey", "load", "SV-0031", shots)
    out = run("survey", "check", "SV-0031", "--share", "0.6")
    assert "3 shots over 1 stations" in out
    assert "sound" in out


def test_a_survey_that_disagrees_with_itself_fails_the_check(run: Book, tmp_path: Path) -> None:
    where = tmp_path / "gauge.csv"
    where.write_text(
        "Date Time,Water Level,Quality\n2025-03-14 06:54,2.000,v\n2025-03-14 07:06,2.000,v\n",
        encoding="utf-8",
    )
    run("tide", "load", "8658120", str(where))
    shots = an_export(
        tmp_path / "shots.csv",
        "100+00,-200,41.2,07:00",
        "100+00,0,41.2,07:00",
        "100+00,0,43.2,07:00",
        "100+00,200,41.2,07:00",
    )
    run("survey", "load", "SV-0031", shots)
    out = run("survey", "check", "SV-0031", "--share", "0.6", ok=False)
    assert "NOT SOUND" in out
    assert "2.00 ft apart" in out
