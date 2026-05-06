"""``scowbox report`` — the printed reports."""

from __future__ import annotations

import datetime as dt

import click

from scowbox.cli.context import opened
from scowbox.cli.options import DEDUCTION, MATERIAL, bulking_of
from scowbox.report import audit as audit_report
from scowbox.report import day as day_report
from scowbox.report import estimate as estimate_report
from scowbox.report import export as export_sheets
from scowbox.report import fleet as fleet_report
from scowbox.report import gauges as gauge_report
from scowbox.report import overdepth as overdepth_report
from scowbox.report import production as production_report
from scowbox.report import reach as reach_report
from scowbox.report import season as season_report
from scowbox.report import section as section_report
from scowbox.report import shoaling as shoaling_report


@click.group()
def report() -> None:
    """Reports off the book."""


def _show(lines: list[str]) -> None:
    """Put a rendered report on the terminal. Eleven commands did this by hand."""
    for line in lines:
        click.echo(line)


@report.command("day")
@click.option(
    "--on",
    "when",
    type=click.DateTime(["%Y-%m-%d"]),
    required=True,
    help="The day to report on.",
)
@click.pass_context
def day(ctx: click.Context, when: dt.datetime) -> None:
    """Everything the book holds about one day."""
    with opened(ctx) as connection:
        lines = day_report.render(connection, when.date())
    _show(lines)


@report.command("reach")
@click.argument("ident")
@MATERIAL
@DEDUCTION
@click.pass_context
def reach(ctx: click.Context, ident: str, material: str, deduction: float) -> None:
    """One reach, its records and its quantity."""
    with opened(ctx) as connection:
        lines = reach_report.render(connection, ident, bulking_of(material), deduction=deduction)
    _show(lines)


@report.command("season")
@MATERIAL
@DEDUCTION
@click.pass_context
def season(ctx: click.Context, material: str, deduction: float) -> None:
    """Where the job stands today."""
    with opened(ctx) as connection:
        lines = season_report.render(connection, bulking_of(material), deduction=deduction)
    _show(lines)


@report.command("audit")
@click.option(
    "--closed-through",
    type=click.DateTime(["%Y-%m-%d"]),
    default=None,
    help="Day the month closed, after which a missing ticket is a violation.",
)
@click.pass_context
def audit(ctx: click.Context, closed_through: dt.datetime | None) -> None:
    """Every place the records and the permits disagree."""
    with opened(ctx) as connection:
        lines = audit_report.render(connection, closed_through.date() if closed_through else None)
    _show(lines)


@report.command("export")
@click.argument("where", type=click.Path(file_okay=False))
@click.pass_context
def export(ctx: click.Context, where: str) -> None:
    """Write the book out as comma separated files."""
    with opened(ctx) as connection:
        written = export_sheets.write(connection, where)
    for path in written:
        click.echo(str(path))


@report.command("production")
@click.option("--reach", default=None, help="Only this reach.")
@MATERIAL
@click.pass_context
def production(ctx: click.Context, reach: str | None, material: str) -> None:
    """Yards moved against the hours it took to move them."""
    with opened(ctx) as connection:
        lines = production_report.render(connection, bulking_of(material), reach=reach)
    _show(lines)


@report.command("shoaling")
@click.option(
    "--min-days",
    type=int,
    default=30,
    show_default=True,
    help="Shortest interval a rate is taken over.",
)
@click.option("--reach", default=None, help="List the quiet intervals on this reach.")
@click.pass_context
def shoaling(ctx: click.Context, min_days: int, reach: str | None) -> None:
    """How fast the channel is filling back in."""
    with opened(ctx) as connection:
        lines = (
            shoaling_report.intervals(connection, reach)
            if reach
            else shoaling_report.render(connection, min_days=min_days)
        )
    _show(lines)


@report.command("gauges")
@click.pass_context
def gauges(ctx: click.Context) -> None:
    """What the gauges cover and which surveys they leave stranded."""
    with opened(ctx) as connection:
        lines = gauge_report.render(connection)
    _show(lines)


@report.command("sections")
@click.argument("ident")
@click.option(
    "--interval",
    type=float,
    default=100.0,
    show_default=True,
    help="Section interval in feet.",
)
@click.pass_context
def sections(ctx: click.Context, ident: str, interval: float) -> None:
    """The end areas and slice volumes behind a reach's survey quantity."""
    with opened(ctx) as connection:
        lines = section_report.render(connection, ident, interval=interval)
    _show(lines)


@report.command("estimate")
@click.argument("ident", required=False, default=None)
@click.option("--item", default=None, help="Follow one line item instead.")
@click.pass_context
def estimate(ctx: click.Context, ident: str | None, item: str | None) -> None:
    """One estimate against the one before it, or the whole history."""
    with opened(ctx) as connection:
        if item is not None:
            lines = estimate_report.item_history(connection, item)
        elif ident is None:
            lines = estimate_report.history(connection)
        else:
            lines = estimate_report.render(connection, ident)
    _show(lines)


@report.command("overdepth")
@click.option(
    "--watch",
    type=float,
    default=0.15,
    show_default=True,
    help="Share of removed material above which a reach is called out.",
)
@MATERIAL
@click.pass_context
def overdepth(ctx: click.Context, watch: float, material: str) -> None:
    """Every yard dug below the pay prism, by reach and by station."""
    with opened(ctx) as connection:
        lines = overdepth_report.render(connection, bulking_of(material), watch=watch)
    _show(lines)


@report.command("fleet")
@click.pass_context
def fleet(ctx: click.Context) -> None:
    """What plant is on the job and what it has done."""
    with opened(ctx) as connection:
        lines = fleet_report.render(connection)
    _show(lines)
