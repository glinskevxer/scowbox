"""``scowbox reach`` — the channel as the contract describes it."""

from __future__ import annotations

import click

from scowbox.model.channel import Method, Reach, Template
from scowbox.store import reaches
from scowbox.store.book import book
from scowbox.units.depth import Depth
from scowbox.units.station import Reachline


@click.group()
def reach() -> None:
    """Reaches of channel and the templates they are cut to."""


@reach.command("add")
@click.argument("ident")
@click.argument("name")
@click.option("--begin", required=True, help="Back station, such as 100+00.")
@click.option("--end", required=True, help="Ahead station, such as 140+00.")
@click.option("--bottom", type=float, required=True, help="Bottom width in feet.")
@click.option("--depth", type=float, required=True, help="Authorized depth in feet.")
@click.option("--slope", type=float, default=3.0, show_default=True, help="Side slope H:1.")
@click.option("--advance", type=float, default=0.0, show_default=True, help="Advance feet.")
@click.option("--overdepth", type=float, default=0.0, show_default=True, help="Paid feet.")
@click.option(
    "--method",
    type=click.Choice([m.value for m in Method]),
    default=Method.SURVEY.value,
    show_default=True,
    help="How this reach is measured for payment.",
)
@click.option("--group", default="base", show_default=True, help="Pay item group.")
@click.pass_context
def add_reach(
    ctx: click.Context,
    ident: str,
    name: str,
    begin: str,
    end: str,
    bottom: float,
    depth: float,
    slope: float,
    advance: float,
    overdepth: float,
    method: str,
    group: str,
) -> None:
    """Put a reach in the book."""
    record = Reach(
        ident=ident,
        name=name,
        line=Reachline.parse(begin, end),
        template=Template(
            bottom_width=bottom,
            authorized_depth=Depth.of_feet(depth),
            side_slope=slope,
            advance_maintenance=advance,
            overdepth=overdepth,
        ),
        method=Method(method),
        group=group,
    )
    with book(ctx.obj["book"]) as connection:
        reaches.add(connection, record)
    click.echo(f"{record.ident} {record.name} {record.line}")


@reach.command("list")
@click.option("--group", default=None, help="Only this pay item group.")
@click.pass_context
def list_reaches(ctx: click.Context, group: str | None) -> None:
    """Every reach in the book, down the channel."""
    with book(ctx.obj["book"]) as connection:
        found = reaches.in_group(connection, group) if group else reaches.listed(connection)
    if not found:
        click.echo("no reaches")
        return
    for record in found:
        click.echo(
            f"{record.ident}  {record.name:<20} {record.line!s:<22}"
            f" {record.template.required_depth}  {record.method.value}"
        )


@reach.command("show")
@click.argument("ident")
@click.pass_context
def show_reach(ctx: click.Context, ident: str) -> None:
    """One reach in full."""
    with book(ctx.obj["book"]) as connection:
        record = reaches.get(connection, ident)
    click.echo(f"{record.ident}  {record.name}")
    click.echo(f"  station    {record.line}  ({record.length:,.0f} ft)")
    click.echo(f"  template   {record.template.describe()}")
    click.echo(f"  authorized {record.template.authorized_depth}")
    click.echo(f"  required   {record.template.required_depth}")
    click.echo(f"  pay        {record.template.pay_depth}")
    click.echo(f"  measured   {record.method.value}")
    click.echo(f"  pay group  {record.group}")


@reach.command("remove")
@click.argument("ident")
@click.pass_context
def remove_reach(ctx: click.Context, ident: str) -> None:
    """Take a reach out of the book."""
    with book(ctx.obj["book"]) as connection:
        reaches.remove(connection, ident)
    click.echo(f"removed {ident}")
