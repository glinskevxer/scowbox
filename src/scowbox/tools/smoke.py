"""A whole job, start to finish, in a throwaway book.

The suite tests every piece. This runs one job through all of them in the order
a real one happens: award the contract, describe the channel, sound it, dig it,
haul it, place it, sound it again, measure it and bill it. It exists because
the pieces have each been right while the join between two of them was not, and
because an installed wheel with a missing module passes every unit test in the
world and fails here.

Every figure it prints is asserted before it is printed.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
import sys
import tempfile
from pathlib import Path

from scowbox.boxmeasure.bulking import typical
from scowbox.datum.tide import TideReading
from scowbox.job.estimating import draft
from scowbox.job.estimating import write as write_estimate
from scowbox.job.quantities import determine_reach
from scowbox.model.channel import Method, Reach, Template
from scowbox.model.contract import Contract, LineItem, Unit
from scowbox.model.placement import Grade, Ground, PlacementArea, PlacementTicket
from scowbox.model.plant import Dredge, Plant
from scowbox.model.scow import BoxReading, Corner, Scow, ScowTrip
from scowbox.model.shift import Downtime, Reason, Shift
from scowbox.model.survey import Sounding, Survey, SurveyKind
from scowbox.model.window import Restriction, Window
from scowbox.store import (
    contracts,
    placements,
    reaches,
    scows,
    shifts,
    surveys,
    tides,
    trips,
    windows,
)
from scowbox.store.book import book
from scowbox.units.clock import moment
from scowbox.units.depth import Depth
from scowbox.units.money import Money
from scowbox.units.station import Reachline, Station
from scowbox.units.volume import Yards

NAME = "smoke"
BEFORE = dt.date(2025, 3, 3)
DUG = dt.date(2025, 3, 10)
AFTER = dt.date(2025, 4, 7)
THROUGH = dt.date(2025, 4, 30)
STATIONS = ("100+00", "101+00", "102+00", "103+00")
OFFSETS = (-300.0, 0.0, 300.0)


def _template() -> Template:
    return Template(
        bottom_width=600,
        authorized_depth=Depth.of_feet(42),
        side_slope=0,
        advance_maintenance=2,
        overdepth=2,
    )


def _survey(ident: str, kind: SurveyKind, day: dt.date, depth: float) -> Survey:
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
            for offset in OFFSETS
        ),
    )


def build(connection: sqlite3.Connection) -> None:
    """Put a whole job in the book."""
    contracts.add(
        connection,
        Contract(
            number="W912PM-25-C-0014",
            awarded=dt.date(2025, 1, 20),
            notice_to_proceed=dt.date(2025, 2, 3),
            days=365,
            retainage=0.05,
            liquidated=Money.parse("$3,400.00"),
            items=(
                LineItem(
                    "LI-0001",
                    "Maintenance dredging, base",
                    Unit.CUBIC_YARD,
                    Money.parse("$7.35"),
                    "base",
                    480000,
                ),
                LineItem("LI-0009", "Mobilisation", Unit.LUMP_SUM, Money.parse("$1,250,000.00")),
            ),
        ),
    )
    reaches.add(
        connection,
        Reach(
            ident="RCH-012",
            name="Lower Range",
            line=Reachline.parse("100+00", "103+00"),
            template=_template(),
            method=Method.BOTH,
            group="base",
        ),
    )
    for day in (BEFORE, AFTER):
        tides.add_readings(
            connection,
            "8658120",
            [
                TideReading(moment(day, "06:54"), 2.0),
                TideReading(moment(day, "07:06"), 2.0),
            ],
        )
    surveys.add(connection, _survey("SV-0031", SurveyKind.BEFORE, BEFORE, 38.0))
    surveys.add(connection, _survey("SV-0032", SurveyKind.AFTER, AFTER, 42.0))
    scows.add(connection, Scow("SC-004", "Dixie 41", 180, 42, 14))
    placements.add(
        connection,
        PlacementArea("PA-002", "Wilmington ODMDS", Ground.OCEAN, "SAW-2019-01142"),
    )
    shifts.add_dredge(
        connection, Dredge("DR-003", "Cherokee", Plant.MECHANICAL, "Norfolk Dredging")
    )
    windows.add(
        connection,
        Window(
            "loggerhead",
            dt.date(2025, 5, 1),
            dt.date(2025, 11, 30),
            Restriction.CLOSED,
            "NMFS",
        ),
    )
    shifts.add(
        connection,
        Shift(
            ident="SH-00021",
            dredge="DR-003",
            reach="RCH-012",
            began=moment(DUG, "06:00"),
            ended=moment(DUG, "18:00"),
            downtimes=(Downtime(moment(DUG, "06:00"), moment(DUG, "13:00"), Reason.WEATHER),),
        ),
    )
    for number in range(14):
        ident = f"TR-{number + 1:05d}"
        trips.add(
            connection,
            ScowTrip(
                ident=ident,
                scow="SC-004",
                reach="RCH-012",
                loaded_on=DUG,
                placement="PA-002",
                readings=tuple(BoxReading(corner, 12.0, 4.0) for corner in Corner),
            ),
        )
        trips.release(
            connection,
            PlacementTicket(
                trip=ident,
                area="PA-002",
                released=moment(DUG, "11:20"),
                yards=Yards.of_yards(2240),
                grade=Grade.SUITABLE,
            ),
        )


def run(quiet: bool = False) -> list[str]:
    """Build a job, measure it, bill it, and check every figure on the way."""
    with (
        tempfile.TemporaryDirectory() as where,
        book(Path(where) / "smoke.sqlite3", create=True) as connection,
    ):
        build(connection)
        found = determine_reach(connection, "RCH-012", typical("silt"))
        assert found.survey is not None, "the survey side produced nothing"
        assert found.scow is not None, "the scow side produced nothing"
        assert found.spread is not None, "a reach measured both ways has a spread"
        assert found.quantity.hundredths > 0, "the job billed nothing"
        drafted = draft(connection, THROUGH, typical("silt"), lump_sums={"LI-0009": 1.0})
        assert drafted.complete, f"a reach was left unmeasured: {drafted.left_out}"
        assert drafted.days_earned == 1, "the rained off day was not credited"
        estimate = write_estimate(connection, drafted)
        assert estimate.due == estimate.payable, "the first estimate owes everything"
        assert estimate.earned.cents > 0, "the estimate earned nothing"
        assert not trips.untick(connection), "a trip left without a ticket"
        lines = [
            f"survey    {found.survey.rounded()}",
            f"scow      {found.scow.rounded()}",
            f"spread    {found.spread:.1%}",
            f"governs   {found.governs.value}",
            f"quantity  {found.quantity.rounded()}",
            f"earned    {estimate.earned}",
            f"retained  {estimate.retained}",
            f"due       {estimate.due}",
        ]
    if not quiet:
        for line in lines:
            print(line)
    return lines


def main(argv: list[str] | None = None) -> int:
    """Run the smoke job and return the exit status."""
    args = sys.argv[1:] if argv is None else argv
    run(quiet="--quiet" in args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
