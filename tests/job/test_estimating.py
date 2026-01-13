"""Drafting an estimate out of what the book can measure today."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from scowbox.boxmeasure.bulking import Bulking
from scowbox.datum.tide import TideReading
from scowbox.errors import RuleError
from scowbox.job.estimating import days_late, draft, write
from scowbox.model.channel import Method, Reach, Template
from scowbox.model.contract import Contract, LineItem, Unit
from scowbox.model.plant import Dredge, Plant
from scowbox.model.shift import Downtime, Reason, Shift
from scowbox.model.survey import Sounding, Survey, SurveyKind
from scowbox.store import contracts, estimates, reaches, shifts, surveys, tides
from scowbox.store.book import book
from scowbox.units.clock import moment
from scowbox.units.depth import Depth
from scowbox.units.money import Money
from scowbox.units.station import Reachline, Station

BEFORE_DAY = dt.date(2025, 7, 1)
AFTER_DAY = dt.date(2025, 8, 1)
THROUGH = dt.date(2025, 8, 31)
NTP = dt.date(2025, 2, 3)
SILT = Bulking("silt", 1.20)
STATIONS = ["100+00", "101+00", "102+00", "103+00"]

CONTRACT = Contract(
    number="W912PM-25-C-0014",
    awarded=dt.date(2025, 1, 20),
    notice_to_proceed=NTP,
    days=365,
    retainage=0.05,
    liquidated=Money.parse("$3,400.00"),
    items=(
        LineItem("LI-0001", "Dredging, base", Unit.CUBIC_YARD, Money.parse("$7.35"), "base"),
        LineItem("LI-0009", "Mobilisation", Unit.LUMP_SUM, Money.parse("$1,250,000.00")),
    ),
)


def a_survey(ident: str, kind: SurveyKind, day: dt.date, depth: float) -> Survey:
    return Survey(
        ident=ident,
        reach="RCH-012",
        kind=kind,
        taken_on=day,
        vessel="Cape Fear",
        transducer_draft=2.0,
        gauge="8658120",
        soundings=tuple(
            Sounding(
                station=Station.parse(station),
                offset=offset,
                raw_depth=Depth.of_feet(depth),
                taken=moment(day, "07:00"),
            )
            for station in STATIONS
            for offset in (-300.0, 0.0, 300.0)
        ),
    )


@pytest.fixture
def open_book(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with book(tmp_path / "book.sqlite3", create=True) as connection:
        contracts.add(connection, CONTRACT)
        reaches.add(
            connection,
            Reach(
                ident="RCH-012",
                name="Lower Range",
                line=Reachline.parse("100+00", "103+00"),
                template=Template(
                    bottom_width=600,
                    authorized_depth=Depth.of_feet(42),
                    side_slope=0,
                    advance_maintenance=2,
                    overdepth=2,
                ),
                method=Method.SURVEY,
                group="base",
            ),
        )
        for day in (BEFORE_DAY, AFTER_DAY):
            tides.add_readings(
                connection,
                "8658120",
                [
                    TideReading(moment(day, "06:54"), 2.0),
                    TideReading(moment(day, "07:06"), 2.0),
                ],
            )
        yield connection


def load(connection: sqlite3.Connection, after: float = 42.0) -> None:
    surveys.add(connection, a_survey("SV-0031", SurveyKind.BEFORE, BEFORE_DAY, 38.0))
    surveys.add(connection, a_survey("SV-0032", SurveyKind.AFTER, AFTER_DAY, after))


def test_a_draft_carries_a_numbered_estimate(open_book: sqlite3.Connection) -> None:
    load(open_book)
    got = draft(open_book, THROUGH, SILT)
    assert got.estimate.number == 1
    assert got.estimate.ident == "EST-001"
    assert got.complete


def test_an_unmeasured_reach_is_named_on_the_draft(open_book: sqlite3.Connection) -> None:
    got = draft(open_book, THROUGH, SILT)
    assert not got.complete
    assert got.left_out[0][0] == "RCH-012"


def test_the_quantity_reaches_the_line(open_book: sqlite3.Connection) -> None:
    load(open_book)
    got = draft(open_book, THROUGH, SILT)
    assert got.estimate.line("LI-0001").to_date == pytest.approx(26666.67, abs=0.1)


def test_a_lump_sum_can_be_claimed(open_book: sqlite3.Connection) -> None:
    load(open_book)
    got = draft(open_book, THROUGH, SILT, lump_sums={"LI-0009": 1.0})
    assert got.estimate.line("LI-0009").earned == Money.parse("$1,250,000.00")


def test_a_written_estimate_comes_back_from_the_book(open_book: sqlite3.Connection) -> None:
    load(open_book)
    write(open_book, draft(open_book, THROUGH, SILT))
    assert estimates.get(open_book, "EST-001").number == 1


def test_the_second_draft_follows_the_first(open_book: sqlite3.Connection) -> None:
    load(open_book)
    write(open_book, draft(open_book, THROUGH, SILT))
    second = draft(open_book, dt.date(2025, 9, 30), SILT)
    assert second.estimate.number == 2
    assert second.estimate.paid_before.cents > 0


def test_an_estimate_cannot_run_back_over_the_last_one(
    open_book: sqlite3.Connection,
) -> None:
    load(open_book)
    write(open_book, draft(open_book, THROUGH, SILT))
    with pytest.raises(RuleError, match="already runs through"):
        draft(open_book, THROUGH, SILT)


def test_nothing_is_late_before_the_contract_runs_out(
    open_book: sqlite3.Connection,
) -> None:
    late, earned = days_late(open_book, THROUGH)
    assert late == 0
    assert earned == 0


def test_days_past_completion_are_counted(open_book: sqlite3.Connection) -> None:
    late, _ = days_late(open_book, CONTRACT.completion + dt.timedelta(days=10))
    assert late == 10


def test_weather_earns_days_back_off_the_lateness(open_book: sqlite3.Connection) -> None:
    shifts.add_dredge(open_book, Dredge("DR-003", "Cherokee", Plant.MECHANICAL, "Norfolk Dredging"))
    day = dt.date(2025, 6, 4)
    shifts.add(
        open_book,
        Shift(
            ident="SH-00021",
            dredge="DR-003",
            reach="RCH-012",
            began=moment(day, "06:00"),
            ended=moment(day, "18:00"),
            downtimes=(Downtime(moment(day, "06:00"), moment(day, "14:00"), Reason.WEATHER),),
        ),
    )
    late, earned = days_late(open_book, CONTRACT.completion + dt.timedelta(days=10))
    assert earned == 1
    assert late == 9


def test_the_lateness_reaches_the_estimate(open_book: sqlite3.Connection) -> None:
    load(open_book)
    got = draft(open_book, CONTRACT.completion + dt.timedelta(days=4), SILT)
    assert got.estimate.days_late == 4
    assert got.estimate.liquidated == Money.parse("$13,600.00")


def test_a_final_estimate_needs_everything_measured(
    open_book: sqlite3.Connection,
) -> None:
    with pytest.raises(RuleError, match="everything measured and ticketed"):
        draft(open_book, THROUGH, SILT, final=True)


def test_a_final_estimate_on_a_clean_book_closes_it(
    open_book: sqlite3.Connection,
) -> None:
    load(open_book)
    got = draft(open_book, THROUGH, SILT, final=True)
    assert got.closeable
    assert got.estimate.final
    assert got.estimate.retained == Money.zero()


def test_a_draft_that_is_not_final_is_built_either_way(
    open_book: sqlite3.Connection,
) -> None:
    got = draft(open_book, THROUGH, SILT)
    assert not got.closeable
    assert not got.estimate.final


def test_the_final_flag_survives_the_book(open_book: sqlite3.Connection) -> None:
    load(open_book)
    write(open_book, draft(open_book, THROUGH, SILT, final=True))
    assert estimates.get(open_book, "EST-001").final
