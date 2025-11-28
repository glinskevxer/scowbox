"""``scowbox reconcile`` settles a reach and puts it back in dispute."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.cli.runner import Book, a_book

SETTLE = [
    "reconcile", "settle", "RCH-012",
    "--accept", "survey", "--on", "2025-11-04", "--by", "R. Beaufort",
]  # fmt: skip


@pytest.fixture
def run(tmp_path: Path) -> Book:
    made = a_book(tmp_path)
    made(
        "reach", "add", "RCH-012", "Lower Range",
        "--begin", "100+00", "--end", "140+00",
        "--bottom", "400", "--depth", "42", "--method", "both",
    )  # fmt: skip
    return made


def test_an_empty_book_has_no_reconciliations(run: Book) -> None:
    assert "no reconciliations" in run("reconcile", "list")


def test_a_settlement_describes_itself(run: Book) -> None:
    out = run(*SETTLE)
    assert "RCH-012 settled 2025-11-04 by R. Beaufort: survey" in out


def test_a_settlement_shows_up_in_the_list(run: Book) -> None:
    run(*SETTLE)
    assert "RCH-012" in run("reconcile", "list")


def test_an_agreed_figure_needs_a_quantity_and_a_note(run: Book) -> None:
    run("reconcile", "settle", "RCH-012", "--accept", "agreed figure",
        "--on", "2025-11-04", "--by", "R. Beaufort", ok=False)  # fmt: skip


def test_an_agreed_figure_carries_both(run: Book) -> None:
    out = run(
        "reconcile", "settle", "RCH-012", "--accept", "agreed figure",
        "--on", "2025-11-04", "--by", "R. Beaufort",
        "--quantity", "24000", "--note", "split the difference",
    )  # fmt: skip
    assert "agreed figure, 24,000 cy" in out
    assert "split the difference" in run("reconcile", "list")


def test_settling_twice_is_refused(run: Book) -> None:
    run(*SETTLE)
    run(*SETTLE, ok=False)


def test_replacing_is_allowed_when_it_is_asked_for(run: Book) -> None:
    run(*SETTLE)
    out = run(*SETTLE[:4], "scow", *SETTLE[5:], "--replace")
    assert "scow" in out


def test_a_reach_that_is_not_there_cannot_be_settled(run: Book) -> None:
    run("reconcile", "settle", "RCH-999", "--accept", "survey",
        "--on", "2025-11-04", "--by", "R. Beaufort", ok=False)  # fmt: skip


def test_dropping_puts_the_reach_back_in_dispute(run: Book) -> None:
    run(*SETTLE)
    assert "back in dispute" in run("reconcile", "drop", "RCH-012")
    assert "no reconciliations" in run("reconcile", "list")


def test_dropping_what_is_not_there_fails(run: Book) -> None:
    run("reconcile", "drop", "RCH-012", ok=False)


def test_nothing_is_outstanding_on_an_unmeasured_book(run: Book) -> None:
    assert "nothing outstanding" in run("reconcile", "open")


def load(run: Book, tmp_path: Path, loads: int) -> None:
    """Measure the reach both ways, with the scows well short of the survey."""
    for day in ("2025-07-01", "2025-08-01"):
        gauge = tmp_path / f"gauge-{day}.csv"
        gauge.write_text(
            f"Date Time,Water Level,Quality\n{day} 06:54,2.000,v\n{day} 07:06,2.000,v\n",
            encoding="utf-8",
        )
        run("tide", "load", "8658120", str(gauge))
    for ident, kind, day, depth in (
        ("SV-0031", "before", "2025-07-01", 38.0),
        ("SV-0032", "after", "2025-08-01", 42.0),
    ):
        run(
            "survey", "add", ident, "RCH-012",
            "--kind", kind, "--on", day,
            "--vessel", "Cape Fear", "--draft", "2.0", "--gauge", "8658120",
        )  # fmt: skip
        shots = tmp_path / f"shots-{ident}.csv"
        rows = [
            f"{station},{offset},{depth},07:00"
            for station in ("100+00", "101+00", "102+00", "103+00")
            for offset in (-300, 0, 300)
        ]
        shots.write_text("station,offset,depth,time\n" + "\n".join(rows) + "\n", encoding="utf-8")
        run("survey", "load", ident, str(shots))
    run("scow", "add", "SC-004", "Dixie 41", "--length", "180", "--width", "42", "--depth", "14")
    run(
        "placement", "add", "PA-002", "Wilmington ODMDS",
        "--ground", "ocean site", "--permit", "SAW-2019-01142",
    )  # fmt: skip
    for number in range(loads):
        ident = f"TR-{number + 1:05d}"
        run(
            "trip", "add", ident, "--scow", "SC-004", "--reach", "RCH-012",
            "--on", "2025-08-01", "--to", "PA-002",
        )  # fmt: skip
        run(
            "trip", "measure", ident,
            "--light", "12", "--pb", "4", "--sb", "4", "--ps", "4", "--ss", "4",
        )  # fmt: skip


@pytest.fixture
def disputed(tmp_path: Path) -> Book:
    made = a_book(tmp_path)
    made(
        "reach", "add", "RCH-012", "Lower Range",
        "--begin", "100+00", "--end", "103+00",
        "--bottom", "600", "--depth", "42", "--slope", "0",
        "--advance", "2", "--overdepth", "2", "--method", "both",
    )  # fmt: skip
    load(made, tmp_path, loads=4)
    return made


def test_a_reach_whose_measurements_disagree_is_listed(disputed: Book) -> None:
    out = disputed("reconcile", "open")
    assert "RCH-012" in out
    assert "survey" in out
    assert "spread" in out


def test_settling_it_takes_it_off_the_list(disputed: Book) -> None:
    disputed(*SETTLE)
    assert "nothing outstanding" in disputed("reconcile", "open")


def test_the_settled_quantity_is_what_the_report_shows(disputed: Book) -> None:
    disputed(*SETTLE)
    out = disputed("quantity", "reach", "RCH-012")
    assert "governs    reconciliation" in out
    assert "26,667 cy" in out


def test_a_stiffer_material_can_close_the_gap(disputed: Book) -> None:
    assert "RCH-012" in disputed("reconcile", "open", "--material", "sand")
