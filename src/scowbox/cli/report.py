"""``scowbox report`` — the printed reports."""

from __future__ import annotations

import datetime as dt

import click

from scowbox.boxmeasure.bulking import materials, typical
from scowbox.cli.context import opened
from scowbox.report import audit as audit_report
from scowbox.report import day as day_report
from scowbox.report import export as export_sheets
from scowbox.report import gauges as gauge_report
from scowbox.report import production as production_report
from scowbox.report import reach as reach_report
from scowbox.report import season as season_report
from scowbox.report import section as section_report
from scowbox.report import shoaling as shoaling_report


@click.group()
def report() -> None:
    """Reports off the book."""


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
    for line in lines:
        click.echo(line)


@report.command("reach")
@click.argument("ident")
@click.option(
    "--material",
    type=click.Choice(materials()),
    default="silt",
    show_default=True,
    help="Material class, which sets the bulking factor.",
)
@click.option(
    "--deduction",
    type=float,
    default=0.0,
    show_default=True,
    help="Share of a scow quantity that falls outside the prism.",
)
@click.pass_context
def reach(ctx: click.Context, ident: str, material: str, deduction: float) -> None:
    """One reach, its records and its quantity."""
    with opened(ctx) as connection:
        lines = reach_report.render(connection, ident, typical(material), deduction=deduction)
    for line in lines:
        click.echo(line)


@report.command("season")
@click.option(
    "--material",
    type=click.Choice(materials()),
    default="silt",
    show_default=True,
    help="Material class, which sets the bulking factor.",
)
@click.option(
    "--deduction",
    type=float,
    default=0.0,
    show_default=True,
    help="Share of a scow quantity that falls outside the prism.",
)
@click.pass_context
def season(ctx: click.Context, material: str, deduction: float) -> None:
    """Where the job stands today."""
    with opened(ctx) as connection:
        lines = season_report.render(connection, typical(material), deduction=deduction)
    for line in lines:
        click.echo(line)


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
    for line in lines:
        click.echo(line)


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
@click.option(
    "--material",
    type=click.Choice(materials()),
    default="silt",
    show_default=True,
    help="Material class, which sets the bulking factor.",
)
@click.pass_context
def production(ctx: click.Context, reach: str | None, material: str) -> None:
    """Yards moved against the hours it took to move them."""
    with opened(ctx) as connection:
        lines = production_report.render(connection, typical(material), reach=reach)
    for line in lines:
        click.echo(line)


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
    for line in lines:
        click.echo(line)


@report.command("gauges")
@click.pass_context
def gauges(ctx: click.Context) -> None:
    """What the gauges cover and which surveys they leave stranded."""
    with opened(ctx) as connection:
        lines = gauge_report.render(connection)
    for line in lines:
        click.echo(line)


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
    for line in lines:
        click.echo(line)
