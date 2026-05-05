"""The fleet report.

What plant is on the job and what it has done. Two tables, because a dredge and
a scow are measured differently: a dredge by the hours it worked and the share
of them it was dredging, a scow by the loads it carried and how full it was
when it carried them.

The share full is the useful column. A scow coming in at half its inside depth
every trip is a scow being loaded to a draft limit somewhere, and twice as many
trips are being run as the box would need.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence

from scowbox.boxmeasure.box import measure
from scowbox.model.scow import ScowTrip
from scowbox.pay.timeloss import tally
from scowbox.report.lines import blank, heading, pair, table
from scowbox.store import scows, shifts, trips
from scowbox.units.volume import Yards, total

DREDGE_WIDTHS = (10, 18, 16, 9, 12, 12)
SCOW_WIDTHS = (10, 14, 9, 8, 16, 12)


def render(connection: sqlite3.Connection) -> list[str]:
    """Every dredge and every scow, with what it has done."""
    lines = heading("Fleet")
    lines.append(blank())
    lines.extend(_dredges(connection))
    lines.append(blank())
    lines.extend(_scows(connection))
    return lines


def _dredges(connection: sqlite3.Connection) -> list[str]:
    held = shifts.dredges(connection)
    if not held:
        return ["No dredge on this job."]
    worked = shifts.listed(connection)
    body = []
    for dredge in held:
        mine = [s for s in worked if s.dredge == dredge.ident]
        got = tally(mine)
        body.append(
            (
                dredge.ident,
                dredge.name,
                dredge.plant.value,
                f"{len(mine):,}",
                f"{got.gross_hours:,.1f}",
                f"{got.share_effective:.0%}" if mine else "-",
            )
        )
    return table(
        ("dredge", "name", "plant", "shifts", "gross hrs", "effective"),
        body,
        DREDGE_WIDTHS,
    )


def _scows(connection: sqlite3.Connection) -> list[str]:
    held = scows.listed(connection)
    if not held:
        return ["No scow on this job."]
    hauled = trips.listed(connection)
    body = []
    for scow in held:
        mine = [t for t in hauled if t.scow == scow.ident]
        measured = [measure(scow, t) for t in mine if t.measured]
        carried = total(m.scow_yards for m in measured)
        full = sum(m.share_full for m in measured) / len(measured) if measured else None
        body.append(
            (
                scow.ident,
                scow.name,
                f"{len(mine):,}",
                f"{len(measured):,}",
                carried.rounded(),
                f"{full:.0%}" if full is not None else "-",
            )
        )
    lines = table(("scow", "name", "trips", "boxed", "carried", "share full"), body, SCOW_WIDTHS)
    lines.append(blank())
    lines.append(pair("trips", f"{len(hauled):,}"))
    lines.append(pair("carried", _carried(connection, hauled).rounded()))
    return lines


def _carried(connection: sqlite3.Connection, hauled: Sequence[ScowTrip]) -> Yards:
    fleet = {s.ident: s for s in scows.listed(connection)}
    return total(
        measure(fleet[t.scow], t).scow_yards for t in hauled if t.measured and t.scow in fleet
    )
