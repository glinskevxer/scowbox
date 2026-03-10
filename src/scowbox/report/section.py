"""The section sheet.

Station by station, the end areas and the volume between them. This is the page
an inspector checks a quantity against, so it prints the arithmetic rather than
the answer: two areas, a length, and the average end area that comes out of
them, on one line each.

The overcut column is the one people look at. It is material that was dug and
hauled and placed and is not paid for, and a reach where it runs at a fifth of
the quantity is a reach where somebody is digging past the prism.
"""

from __future__ import annotations

import sqlite3

from scowbox.job.quantities import survey_side
from scowbox.report.lines import blank, heading, pair, table, total_line
from scowbox.section.area import SectionArea
from scowbox.section.volume import Slice
from scowbox.store import reaches

AREA_WIDTHS = (10, 14, 14, 14, 10, 10)
SLICE_WIDTHS = (10, 10, 9, 14, 14, 14)


def render(connection: sqlite3.Connection, ident: str, *, interval: float = 100.0) -> list[str]:
    """Every section and every slice of one reach's survey quantity."""
    reach = reaches.get(connection, ident)
    found = survey_side(connection, reach, interval=interval)
    lines = heading(f"Sections, {reach.ident}  {reach.name}")
    lines.append(blank())
    lines.append(pair("surveys", f"{found.before} before, {found.after} after"))
    lines.append(pair("template", reach.template.describe()))
    lines.append(
        pair("sections", f"{found.sections:,} of {found.sections + len(found.unpaired):,}")
    )
    lines.append(blank())
    lines.extend(_areas(found.areas))
    lines.append(blank())
    lines.extend(_slices(found.volume.slices))
    return lines


def _areas(areas: tuple[SectionArea, ...]) -> list[str]:
    body = [
        (
            str(area.station),
            f"{area.removed:,.1f}",
            f"{area.pay:,.1f}",
            f"{area.overcut:,.1f}",
            f"{area.left:,.0f}",
            f"{area.right:,.0f}",
        )
        for area in areas
    ]
    return table(
        ("station", "removed sf", "pay sf", "overcut sf", "left", "right"), body, AREA_WIDTHS
    )


def _slices(slices: tuple[Slice, ...]) -> list[str]:
    body = [
        (
            str(one.begin),
            str(one.end),
            f"{one.length:,.0f}",
            one.removed.rounded(),
            one.pay.rounded(),
            one.overcut.rounded(),
        )
        for one in slices
    ]
    lines = table(("from", "to", "length", "removed", "pay", "overcut"), body, SLICE_WIDTHS)
    removed = sum(one.removed.hundredths for one in slices)
    pay = sum(one.pay.hundredths for one in slices)
    lines.append(blank())
    lines.append(total_line("total", f"{removed / 100:,.0f} cy removed", (10, 10, 9, 30)))
    lines.append(total_line("", f"{pay / 100:,.0f} cy pay", (10, 10, 9, 30)))
    lines.append(total_line("", f"{(removed - pay) / 100:,.0f} cy overcut", (10, 10, 9, 30)))
    return lines
