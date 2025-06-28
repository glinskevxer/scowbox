"""``scowbox placement`` — where the material is allowed to go."""

from __future__ import annotations

import click

from scowbox.measure.placing import standing
from scowbox.model.placement import Ground, PlacementArea
from scowbox.store import placements, trips
from scowbox.store.book import book
from scowbox.units.volume import Yards


@click.group()
def placement() -> None:
    """Permitted placement areas and what is in them."""


@placement.command("add")
@click.argument("ident")
@click.argument("name")
@click.option(
    "--ground",
    type=click.Choice([g.value for g in Ground]),
    required=True,
    help="What kind of place it is.",
)
@click.option("--permit", required=True, help="The permit it is placed under.")
@click.option("--capacity", type=float, default=None, help="Capacity in cubic yards.")
@click.pass_context
def add_placement(
    ctx: click.Context,
    ident: str,
    name: str,
    ground: str,
    permit: str,
    capacity: float | None,
) -> None:
    """Put a placement area in the book."""
    area = PlacementArea(
        ident=ident,
        name=name,
        ground=Ground(ground),
        permit=permit,
        capacity=None if capacity is None else Yards.of_yards(capacity),
    )
    with book(ctx.obj["book"]) as connection:
        placements.add(connection, area)
    click.echo(f"{area.ident} {area.name}, {area.ground.value}, permit {area.permit}")


@placement.command("list")
@click.pass_context
def list_placements(ctx: click.Context) -> None:
    """Every placement area and how full it is."""
    with book(ctx.obj["book"]) as connection:
        found = placements.listed(connection)
        held = {
            area.ident: standing(area, trips.tickets_for_area(connection, area.ident))
            for area in found
        }
    if not found:
        click.echo("no placement areas")
        return
    for area in found:
        total = held[area.ident]
        room = "open" if total.remaining is None else f"{total.remaining} left"
        click.echo(
            f"{area.ident}  {area.name:<24} {area.ground.value:<18}"
            f" {total.tickets:>4} loads  {room}"
        )


@placement.command("show")
@click.argument("ident")
@click.pass_context
def show_placement(ctx: click.Context, ident: str) -> None:
    """One placement area, what it takes and what is in it."""
    with book(ctx.obj["book"]) as connection:
        area = placements.get(connection, ident)
        total = standing(area, trips.tickets_for_area(connection, ident))
    click.echo(f"{area.ident}  {area.name}")
    click.echo(f"  ground     {area.ground.value}")
    click.echo(f"  permit     {area.permit}")
    click.echo(f"  takes      {', '.join(sorted(g.value for g in area.ground.takes))}")
    click.echo(f"  loads      {total.tickets:,}")
    click.echo(f"  placed     {total.placed}")
    if total.capacity is None:
        click.echo("  capacity   open")
    else:
        click.echo(f"  capacity   {total.capacity}, {total.share_used:.1%} used")
