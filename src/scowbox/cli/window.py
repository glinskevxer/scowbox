"""``scowbox window`` — the environmental calendar."""

from __future__ import annotations

import datetime as dt

import click

from scowbox.model.window import ALL_REACHES, Restriction, Window
from scowbox.store import windows
from scowbox.store.book import book


@click.group()
def window() -> None:
    """Environmental windows and what they close."""


@window.command("add")
@click.argument("name")
@click.option("--from", "begins", type=click.DateTime(["%Y-%m-%d"]), required=True)
@click.option("--to", "ends", type=click.DateTime(["%Y-%m-%d"]), required=True)
@click.option(
    "--restriction",
    type=click.Choice([r.value for r in Restriction]),
    required=True,
    help="What the window does while it is in force.",
)
@click.option("--authority", required=True, help="Who imposed it.")
@click.option("--reach", default=ALL_REACHES, help="One reach, or all of them by default.")
@click.pass_context
def add_window(
    ctx: click.Context,
    name: str,
    begins: dt.datetime,
    ends: dt.datetime,
    restriction: str,
    authority: str,
    reach: str,
) -> None:
    """Put an environmental window in the book."""
    record = Window(
        name=name,
        begins=begins.date(),
        ends=ends.date(),
        restriction=Restriction(restriction),
        authority=authority,
        reach=reach,
    )
    with book(ctx.obj["book"]) as connection:
        windows.add(connection, record)
    click.echo(record.describe())


@window.command("list")
@click.pass_context
def list_windows(ctx: click.Context) -> None:
    """Every window in the book, in date order."""
    with book(ctx.obj["book"]) as connection:
        found = windows.listed(connection)
    if not found:
        click.echo("no windows")
        return
    for record in found:
        click.echo(f"{record.describe()}  ({record.days:,} days)")


@window.command("on")
@click.argument("day", type=click.DateTime(["%Y-%m-%d"]))
@click.argument("reach")
@click.pass_context
def window_on(ctx: click.Context, day: dt.datetime, reach: str) -> None:
    """What governs one reach on one day."""
    with book(ctx.obj["book"]) as connection:
        found = windows.covering(connection, day.date(), reach)
        schedule = windows.schedule(connection)
    governs = schedule.on(day.date(), reach)
    click.echo(f"{reach} on {day:%Y-%m-%d}: {governs.value}")
    for record in found:
        click.echo(f"  {record.name} ({record.authority}) {record.restriction.value}")
    if governs.stops_work:
        opens = schedule.next_open(day.date(), reach)
        click.echo(f"  opens {opens}" if opens else "  opens: not within a year")
