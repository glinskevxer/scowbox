"""``scowbox survey`` — surveys, and loading the shots into them."""

from __future__ import annotations

import datetime as dt

import click

from scowbox.cli.context import opened
from scowbox.feed.soundings import kept, parse_file, refused
from scowbox.model.survey import Survey, SurveyKind
from scowbox.store import surveys


@click.group()
def survey() -> None:
    """Hydrographic surveys and their soundings."""


@survey.command("add")
@click.argument("ident")
@click.argument("reach")
@click.option(
    "--kind",
    type=click.Choice([k.value for k in SurveyKind]),
    required=True,
    help="What the survey is for.",
)
@click.option(
    "--on",
    "taken_on",
    type=click.DateTime(["%Y-%m-%d"]),
    required=True,
    help="The day the survey was run.",
)
@click.option("--vessel", required=True, help="The boat that ran it.")
@click.option("--draft", type=float, required=True, help="Transducer draft in feet.")
@click.option("--gauge", default="", help="Gauge the shots reduce against.")
@click.pass_context
def add_survey(
    ctx: click.Context,
    ident: str,
    reach: str,
    kind: str,
    taken_on: dt.datetime,
    vessel: str,
    draft: float,
    gauge: str,
) -> None:
    """Put a survey header in the book."""
    record = Survey(
        ident=ident,
        reach=reach,
        kind=SurveyKind(kind),
        taken_on=taken_on.date(),
        vessel=vessel,
        transducer_draft=draft,
        gauge=gauge,
    )
    with opened(ctx) as connection:
        surveys.add(connection, record)
    click.echo(f"{record.ident} {record.kind.value} of {record.reach} on {record.taken_on}")


@survey.command("load")
@click.argument("ident")
@click.argument("export", type=click.Path(exists=True, dir_okay=False))
@click.option("--show-refused", is_flag=True, help="Print every line that would not read.")
@click.pass_context
def load_survey(ctx: click.Context, ident: str, export: str, show_refused: bool) -> None:
    """Load a sounding export into a survey, replacing what is there."""
    with opened(ctx) as connection:
        header = surveys.get(connection, ident)
        readings = parse_file(export, header.taken_on)
        gone, arrived = surveys.load(connection, ident, kept(readings))
    click.echo(f"{ident}: {arrived:,} shots loaded, {gone:,} replaced")
    bad = refused(readings)
    if bad:
        click.echo(f"{len(bad):,} lines would not read")
    if show_refused:
        for reading in bad:
            click.echo(f"  line {reading.line}: {reading.trouble}")


@survey.command("list")
@click.option("--reach", default=None, help="Only surveys of this reach.")
@click.pass_context
def list_surveys(ctx: click.Context, reach: str | None) -> None:
    """Every survey in the book, oldest first."""
    with opened(ctx) as connection:
        found = surveys.for_reach(connection, reach) if reach else surveys.listed(connection)
    if not found:
        click.echo("no surveys")
        return
    for record in found:
        click.echo(
            f"{record.ident}  {record.taken_on}  {record.reach}"
            f"  {record.kind.value:<9} {record.vessel}"
        )


@survey.command("show")
@click.argument("ident")
@click.pass_context
def show_survey(ctx: click.Context, ident: str) -> None:
    """One survey with a count of what it holds."""
    with opened(ctx) as connection:
        record = surveys.full(connection, ident)
    click.echo(f"{record.ident}  {record.kind.value} of {record.reach}")
    click.echo(f"  taken      {record.taken_on} by {record.vessel}")
    click.echo(f"  draft      {record.transducer_draft:g} ft")
    click.echo(f"  gauge      {record.gauge or 'none named'}")
    click.echo(f"  soundings  {record.count:,}")
    stations = record.stations()
    if stations:
        click.echo(f"  stations   {len(stations):,} from {stations[0]} to {stations[-1]}")
    click.echo(f"  pays       {'yes' if record.kind.pays else 'no'}")
