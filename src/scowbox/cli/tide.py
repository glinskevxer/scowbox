"""``scowbox tide`` — gauge readings."""

from __future__ import annotations

import datetime as dt

import click

from scowbox.cli.context import opened
from scowbox.feed.tides import parse_file
from scowbox.store import tides


@click.group()
def tide() -> None:
    """Water level readings the soundings are reduced against."""


@tide.command("load")
@click.argument("gauge")
@click.argument("download", type=click.Path(exists=True, dir_okay=False))
@click.pass_context
def load_tide(ctx: click.Context, gauge: str, download: str) -> None:
    """Load a water level download for one gauge."""
    parsed = parse_file(download, gauge)
    with opened(ctx) as connection:
        written = tides.add_readings(connection, gauge, parsed.readings)
    click.echo(f"{gauge}: {parsed.count:,} read, {written:,} new")
    if parsed.preliminary:
        click.echo(f"  {parsed.preliminary:,} preliminary, subject to change when verified")
    if parsed.flagged:
        click.echo(f"  {parsed.flagged:,} left out on the flat tolerance flag")
    if parsed.refused:
        click.echo(f"  {len(parsed.refused):,} lines would not read")


@tide.command("list")
@click.pass_context
def list_tides(ctx: click.Context) -> None:
    """Every gauge the book holds readings for, and what it covers."""
    with opened(ctx) as connection:
        found = tides.gauges(connection)
        if not found:
            click.echo("no gauges")
            return
        for gauge in found:
            first, last = tides.span(connection, gauge)
            click.echo(f"{gauge}  {first:%Y-%m-%d %H:%M} to {last:%Y-%m-%d %H:%M}")


@tide.command("at")
@click.argument("gauge")
@click.argument("when")
@click.pass_context
def tide_at(ctx: click.Context, gauge: str, when: str) -> None:
    """The interpolated height at one moment, as the reduction would use it."""
    moment = dt.datetime.fromisoformat(when)
    with opened(ctx) as connection:
        record = tides.record_for(connection, gauge, moment, moment)
    click.echo(f"{gauge} at {when}: {record.height_at(moment):+.3f} ft")
