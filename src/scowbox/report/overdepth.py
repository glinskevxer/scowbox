"""The overdepth report.

Every yard the contractor dug below the pay prism, by reach and by station. It
is the report nobody asks for until the quantity comes in high, and by then the
work is done and the argument is about whether it should have been.

The share is against removed rather than against pay, because that is the
question: of everything that came out, how much was never going to be paid for.
A reach at five percent is a normal cut. A reach at a third is a bucket being
worked two feet low, and the stations where it happened are on the page.
"""

from __future__ import annotations

import sqlite3

from scowbox.boxmeasure.bulking import Bulking
from scowbox.job.quantities import determined, survey_side
from scowbox.report.lines import blank, heading, indent, pair, table
from scowbox.section.area import SectionArea
from scowbox.store import reaches

WATCH = 0.15
WIDTHS = (10, 16, 16, 16, 10)


def share_of(area: SectionArea) -> float:
    """The share of a section's removed material that fell outside the prism."""
    if area.removed <= 0:
        return 0.0
    return round(area.overcut / area.removed, 4)


def render(connection: sqlite3.Connection, bulking: Bulking, *, watch: float = WATCH) -> list[str]:
    """Overcut by reach, with the worst stations named."""
    lines = heading("Overdepth")
    lines.append(blank())
    lines.append(pair("watch above", f"{watch:.0%} of removed material"))
    lines.append(blank())
    body = []
    notes: list[str] = []
    for reach in reaches.listed(connection):
        found = determined(connection, reach.ident, bulking)
        if found is None or not reach.method.takes_survey:
            notes.append(f"{reach.ident}  no survey quantity to take an overcut from")
            continue
        worked = survey_side(connection, reach)
        volume = worked.volume
        share = (
            0.0
            if volume.removed.hundredths == 0
            else round(volume.overcut.hundredths / volume.removed.hundredths, 4)
        )
        body.append(
            (
                reach.ident,
                volume.removed.rounded(),
                volume.pay.rounded(),
                volume.overcut.rounded(),
                f"{share:.1%}",
            )
        )
        if share > watch:
            notes.extend(_stations(reach.ident, worked.areas, watch))
    if body:
        lines.extend(table(("reach", "removed", "pay", "overcut", "share"), body, WIDTHS))
    else:
        lines.append("No reach has a survey quantity to take an overcut from.")
    if notes:
        lines.append(blank())
        lines.extend(notes)
    return lines


def _stations(reach: str, areas: tuple[SectionArea, ...], watch: float) -> list[str]:
    worst = sorted(areas, key=lambda a: -share_of(a))
    over = [a for a in worst if share_of(a) > watch]
    return [
        f"{reach} is over the watch on {len(over):,} of {len(areas):,} sections",
        *indent(
            f"{a.station}: {a.overcut:,.0f} of {a.removed:,.0f} sq ft, {share_of(a):.1%}"
            for a in over[:10]
        ),
    ]
