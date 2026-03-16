"""Loading a reach's surveys through the command line.

Three command line suites had written this out, and they had drifted in the
depths they used, so a change to the pay prism moved two of them and not the
third. The numbers live here now: a four foot cut on a six hundred foot bottom,
which is twenty six thousand six hundred and sixty seven cubic yards.
"""

from __future__ import annotations

from pathlib import Path

from tests.cli.runner import Book

GAUGE = "8658120"
STATIONS = ("100+00", "101+00", "102+00", "103+00")
OFFSETS = (-300, 0, 300)
BEFORE_DAY = "2025-07-01"
AFTER_DAY = "2025-08-01"


def a_reach(run: Book, ident: str = "RCH-012", method: str = "survey") -> None:
    """A three hundred foot reach with a six hundred foot bottom."""
    run(
        "reach", "add", ident, "Lower Range",
        "--begin", "100+00", "--end", "103+00",
        "--bottom", "600", "--depth", "42", "--slope", "0",
        "--advance", "2", "--overdepth", "2", "--method", method,
    )  # fmt: skip


def load_tide(run: Book, tmp_path: Path, day: str) -> None:
    """A flat two foot tide over the hour the shots were taken."""
    where = tmp_path / f"gauge-{day}.csv"
    where.write_text(
        f"Date Time,Water Level,Quality\n{day} 06:54,2.000,v\n{day} 07:06,2.000,v\n",
        encoding="utf-8",
    )
    run("tide", "load", GAUGE, str(where))


def load_survey(
    run: Book,
    tmp_path: Path,
    ident: str,
    kind: str,
    day: str,
    depth: float,
    reach: str = "RCH-012",
) -> None:
    """A survey of one reach at one flat depth."""
    run(
        "survey", "add", ident, reach,
        "--kind", kind, "--on", day,
        "--vessel", "Cape Fear", "--draft", "2.0", "--gauge", GAUGE,
    )  # fmt: skip
    where = tmp_path / f"shots-{ident}.csv"
    rows = [f"{station},{offset},{depth},07:00" for station in STATIONS for offset in OFFSETS]
    where.write_text("station,offset,depth,time\n" + "\n".join(rows) + "\n", encoding="utf-8")
    run("survey", "load", ident, str(where))


def survey_the_reach(run: Book, tmp_path: Path, before: float = 38.0, after: float = 42.0) -> None:
    """Both surveys and the tide behind them, for a four foot cut."""
    load_tide(run, tmp_path, BEFORE_DAY)
    load_tide(run, tmp_path, AFTER_DAY)
    load_survey(run, tmp_path, "SV-0031", "before", BEFORE_DAY, before)
    load_survey(run, tmp_path, "SV-0032", "after", AFTER_DAY, after)
