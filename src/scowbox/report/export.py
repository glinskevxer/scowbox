"""Getting the book out as comma separated text.

Everything in here ends up in somebody's spreadsheet, so the columns are named
the way the domain names them and the numbers are written plain: no thousands
separators, no dollar signs, no units in the cell. A cubic yard column that
says ``26,666.67 cy`` is a text column, and a text column cannot be summed.

Money is written in dollars and cents as a plain decimal, which is the one
place this program lets a value out of integer cents. It is the last thing that
happens to it.
"""

from __future__ import annotations

import csv
import sqlite3
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from scowbox.boxmeasure.box import measure
from scowbox.errors import MissingError, RuleError
from scowbox.store import contracts, estimates, reaches, scows, shifts, surveys, trips

Row = Sequence[object]


@dataclass(frozen=True)
class Sheet:
    """One file of the export."""

    name: str
    headings: tuple[str, ...]
    rows: tuple[Row, ...]

    @property
    def filename(self) -> str:
        return f"{self.name}.csv"


def reach_sheet(connection: sqlite3.Connection) -> Sheet:
    """The channel as the contract describes it."""
    return Sheet(
        "reaches",
        (
            "reach",
            "name",
            "station_begin",
            "station_end",
            "length_ft",
            "bottom_width_ft",
            "authorized_ft",
            "required_ft",
            "pay_ft",
            "side_slope",
            "method",
            "pay_group",
        ),
        tuple(
            (
                r.ident,
                r.name,
                str(r.line.begin),
                str(r.line.end),
                f"{r.length:.2f}",
                f"{r.template.bottom_width:.2f}",
                f"{r.template.authorized_depth.feet:.2f}",
                f"{r.template.required_depth.feet:.2f}",
                f"{r.template.pay_depth.feet:.2f}",
                f"{r.template.side_slope:g}",
                r.method.value,
                r.group,
            )
            for r in reaches.listed(connection)
        ),
    )


def survey_sheet(connection: sqlite3.Connection) -> Sheet:
    """Every survey and how many shots it carries."""
    return Sheet(
        "surveys",
        ("survey", "reach", "kind", "taken_on", "vessel", "draft_ft", "gauge", "soundings"),
        tuple(
            (
                s.ident,
                s.reach,
                s.kind.value,
                s.taken_on.isoformat(),
                s.vessel,
                f"{s.transducer_draft:.2f}",
                s.gauge,
                surveys.full(connection, s.ident).count,
            )
            for s in surveys.listed(connection)
        ),
    )


def trip_sheet(connection: sqlite3.Connection) -> Sheet:
    """Every scow trip with its box measure and its ticket."""
    fleet = {s.ident: s for s in scows.listed(connection)}
    rows = []
    for trip in trips.listed(connection):
        yards = ""
        mean = ""
        if trip.measured and trip.scow in fleet:
            try:
                got = measure(fleet[trip.scow], trip)
            except RuleError:
                got = None
            if got is not None:
                yards = f"{got.scow_yards.yards:.2f}"
                mean = f"{got.mean_material:.2f}"
        try:
            ticket = trips.ticket_of(connection, trip.ident)
            area, released, grade = (
                ticket.area,
                ticket.released.isoformat(),
                ticket.grade.value,
            )
        except MissingError:
            area, released, grade = "", "", ""
        rows.append(
            (
                trip.ident,
                trip.scow,
                trip.reach,
                trip.loaded_on.isoformat(),
                mean,
                yards,
                area,
                released,
                grade,
            )
        )
    return Sheet(
        "trips",
        (
            "trip",
            "scow",
            "reach",
            "loaded_on",
            "mean_material_ft",
            "scow_yards",
            "placement",
            "released",
            "grade",
        ),
        tuple(rows),
    )


def shift_sheet(connection: sqlite3.Connection) -> Sheet:
    """Every shift and the hours on it."""
    return Sheet(
        "shifts",
        ("shift", "dredge", "reach", "day", "gross_hours", "down_hours", "effective_hours"),
        tuple(
            (
                s.ident,
                s.dredge,
                s.reach,
                s.day.isoformat(),
                f"{s.gross_hours:.2f}",
                f"{s.down_minutes / 60:.2f}",
                f"{s.effective_hours:.2f}",
            )
            for s in shifts.listed(connection)
        ),
    )


def estimate_sheet(connection: sqlite3.Connection) -> Sheet:
    """Every estimate line ever written, one row each."""
    rows: list[Row] = []
    for number in contracts.numbers(connection):
        for one in estimates.listed(connection, number):
            rows.extend(
                (
                    one.ident,
                    number,
                    one.through.isoformat(),
                    line.item,
                    line.unit.value,
                    f"{line.unit_price.dollars:.2f}",
                    f"{line.to_date:.2f}",
                    f"{line.this_period:.2f}",
                    f"{line.earned.dollars:.2f}",
                )
                for line in one.lines
            )
    return Sheet(
        "estimates",
        (
            "estimate",
            "contract",
            "through",
            "item",
            "unit",
            "unit_price",
            "to_date",
            "this_period",
            "earned",
        ),
        tuple(rows),
    )


def sheets(connection: sqlite3.Connection) -> Iterator[Sheet]:
    """Every sheet of the export, in a fixed order."""
    yield reach_sheet(connection)
    yield survey_sheet(connection)
    yield trip_sheet(connection)
    yield shift_sheet(connection)
    yield estimate_sheet(connection)


def write(connection: sqlite3.Connection, where: str | Path) -> list[Path]:
    """Write every sheet into a directory and return what was written."""
    folder = Path(where)
    folder.mkdir(parents=True, exist_ok=True)
    written = []
    for sheet in sheets(connection):
        target = folder / sheet.filename
        with target.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(sheet.headings)
            writer.writerows(sheet.rows)
        written.append(target)
    return written
