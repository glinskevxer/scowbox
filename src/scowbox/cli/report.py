"""``scowbox report`` — the printed reports."""

from __future__ import annotations

import datetime as dt

import click

from scowbox.boxmeasure.bulking import materials, typical
from scowbox.report import day as day_report
from scowbox.report import reach as reach_report
from scowbox.store.book import book


@click.group()
def report() -> None:
    """Reports off the book."""


@report.command("day")
@click.option("--on", "when", type=click.DateTime(["%Y-%m-%d"]), required=True)
@click.pass_context
def day(ctx: click.Context, when: dt.datetime) -> None:
    """Everything the book holds about one day."""
    with book(ctx.obj["book"]) as connection:
        lines = day_report.render(connection, when.date())
    for line in lines:
        click.echo(line)


@report.command("reach")
@click.argument("ident")
@click.option("--material", type=click.Choice(materials()), default="silt", show_default=True)
@click.option("--deduction", type=float, default=0.0, show_default=True)
@click.pass_context
def reach(ctx: click.Context, ident: str, material: str, deduction: float) -> None:
    """One reach, its records and its quantity."""
    with book(ctx.obj["book"]) as connection:
        lines = reach_report.render(connection, ident, typical(material), deduction=deduction)
    for line in lines:
        click.echo(line)
